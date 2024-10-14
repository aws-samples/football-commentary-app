import json
import boto3
import os
import base64
import time

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['TABLE_NAME']
table = dynamodb.Table(table_name)

# Bedrock
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-west-2',
)

model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
# model_id = 'mistral.mistral-large-2407-v1:0'

# TODO: Add a KB to the team / season so it can use that in the comm
def preprocess_prompt(kinesis_record):
    # Parse the Kinesis record data
    try:
        event = json.loads(kinesis_record)
    except json.JSONDecodeError:
        print("Error: Unable to parse Kinesis record as JSON")
        return None
#     event_field_descriptions = """
#     Here are the Soccer match event descriptions:

# minute: The minute of the match when the event occurred
# event_type: The primary type of event (e.g., Foul, Attempt, Corner, Substitution)
# event_type2: A secondary event type, if applicable (e.g., Key Pass, Failed through ball)
# side: Indicates whether the event is for the Home or Away team
# event_team: The name of the team involved in the event
# opponent: The name of the opposing team
# player: The name of the primary player involved in the event
# is_goal: Indicates whether the event resulted in a goal
# assisted_by_player: The name of the player who assisted in the event, if applicable
# shot_place: The location where the shot was directed (for attempt events)
# shot_outcome: The result of the shot (e.g., On target, Off target, Blocked)
# location: The area of the field where the event occurred
# bodypart: The body part used for the action (mainly for attempt events)
# assist_method: The method of assist (e.g., Pass, Cross, Headed pass)
# situation: The game situation during the event (e.g., Open play, Set piece)
# shot_speed: The speed of the shot in km/h (for attempt events)
# goal_probability: The estimated probability of scoring from the attempt, as a percentage
# distance_to_goal: The distance from which the shot was taken, in meters
# player_in: The name of the player coming onto the field (for substitution events)
# player_out: The name of the player leaving the field (for substitution events)"""


    # Extract relevant information from the event
    event_type = event.get('event_type', 'Unknown')
    minute = event.get('minute', 0)
    team = event.get('event_team', 'Unknown team')
    player = event.get('player', 'Unknown player')
    opponent = event.get('opponent', 'Unknown opponent')
    location = event.get('location', '')
    is_goal = event.get('is_goal', False)

    # Additional details for specific event types
    additional_details = ''
    if event_type == 'Attempt':
        shot_outcome = event.get('shot_outcome', '')
        shot_place = event.get('shot_place', '')
        bodypart = event.get('bodypart', '')
        distance_to_goal = event.get('distance_to_goal', ''),
        additional_details = f"Shot outcome: {shot_outcome}, Shot place: {shot_place}, Body part: {bodypart}, Distance to Goal: {distance_to_goal}",
    elif event_type in ['Yellow card', 'Red card']:
        additional_details = f"Card type: {event_type}"
    elif event_type == 'Substitution':
        player_in = event.get('player_in', '')
        player_out = event.get('player_out', '')
        additional_details = f"Player in: {player_in}, Player out: {player_out}"

    # Create a context-specific prompt for the LLM
    prompt = f"""Here is the event:

Event Type: {event_type}
Minute: {minute}
Team: {team}
Player: {player}
Opponent: {opponent}
Location: {location}
Was a Goal scored in this event: {'Yes' if is_goal else 'No'}
{additional_details}

Commentary:"""

    message = {
        "role": "user",
        "content": [{"text": prompt}]
    }

    return (message)

def handler(event, context):
    # Process Kinesis records and write to DynamoDB
    for record in event['Records']:
        print("DEBUG RECORD:")
        print(record)
        try:
            payload = base64.b64decode(
                    record['kinesis']['data']
                    ).decode("utf-8")
            print("DEBUG PAYLOAD:")
            print(payload)
            prompt = preprocess_prompt(payload)
        except Exception as e:
            print(f"An error occurred {e}")
            raise e

        message_history_request = table.get_item(Key={'id': 'latest'})
        if 'Item' in message_history_request:
            messages = message_history_request['Item']['comment']
        else:
            messages = []

        messages.append(prompt)

        print("DEBUG:")
        print(messages)

        inference_config = {
            'temperature': 0.9,
            'topP': 0.95,
            'maxTokens': 2048
        }

        system_prompt = {"text": "You are an enthusiastic soccer commentator for social media. This is formatted event data coming from a news source. Generate a single sentence of commentary that captures the excitement and significance of this moment in the match. Be creative and use varied language to keep the commentary engaging. If it's a goal, make it extra exciting! Use Emojis where it makes sense"}

        response = bedrock.converse(
            messages=messages,
            modelId=model_id,
            inferenceConfig=inference_config,
            system=[system_prompt],
        )

        # Parse the response
        comment = response['output']['message']['content'][0]['text']
        messages.append(response['output']['message'])

        print(f"Generated comment: {comment}")

        try:
            ddb_response = table.put_item(
                Item={
                    'id': 'latest',
                    'comment': messages,
                    'timestamp': int(time.time())
                }
            )
        except Exception as e:
            print(f"Error writing item from DynamoDB: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps('Succesfully processed {} events'.format(len(event['Records'])))
    }
