import json
import boto3
import os
import base64
from datetime import datetime

# DynamoDB
dynamodb = boto3.resource("dynamodb")
table_name = os.environ["TABLE_NAME"]
table = dynamodb.Table(table_name)

# Bedrock
bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-west-2",
)

model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"


# TODO: Add a KB to the team / season so it can use that in the comm
def preprocess_prompt(kinesis_record):
    # Parse the Kinesis record data
    try:
        event = json.loads(kinesis_record)
    except json.JSONDecodeError:
        print("Error: Unable to parse Kinesis record as JSON")
        return None

    # Extract relevant information from the event
    event_type = event.get("event_type", "Unknown")
    minute = event.get("minute", 0)
    team = event.get("event_team", "Unknown team")
    player = event.get("player", "Unknown player")
    opponent = event.get("opponent", "Unknown opponent")
    location = event.get("location", "")
    is_goal = event.get("is_goal", False)

    # Additional details for specific event types
    additional_details = ""
    if event_type == "Attempt":
        shot_outcome = event.get("shot_outcome", "")
        shot_place = event.get("shot_place", "")
        bodypart = event.get("bodypart", "")
        distance_to_goal = (event.get("distance_to_goal", ""),)
        additional_details = (
            f"Shot outcome: {shot_outcome}, \
                Shot place: {shot_place}, \
                Body part: {bodypart}, \
                Distance to Goal: {distance_to_goal}",
        )
    elif event_type in ["Yellow card", "Red card"]:
        additional_details = f"Card type: {event_type}"
    elif event_type == "Substitution":
        player_in = event.get("player_in", "")
        player_out = event.get("player_out", "")
        additional_details = f"Player in: {player_in}, \
                Player out: {player_out}"

    # Create a context-specific prompt for the LLM
    prompt = f"""You are an enthusiastic soccer commentator. This is formatted event data coming from a news source. Generate a single sentence of commentary that captures the excitement and significance of this moment in the match. Be creative and use varied language to keep the commentary engaging. If it's a goal, make it extra exciting! Here is the event:

Event Type: {event_type}
Minute: {minute}
Team: {team}
Player: {player}
Opponent: {opponent}
Location: {location}
Was a Goal scored in this event: {'Yes' if is_goal else 'No'}
{additional_details}

Commentary:"""

    # Prepare the LLM payload
    # TODO: Convert to Converse API calls and store them in DynamoDB
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "max_tokens": 400,  # Adjust as needed
        "temperature": 0.9,  # Slightly increase creativity
        "top_p": 0.95,
        "top_k": 250,
    }

    return json.dumps(payload)


def handler(event, context):
    # Process Kinesis records and write to DynamoDB
    for record in event["Records"]:
        payload = base64.b64decode(record["kinesis"]["data"])
        prompt = preprocess_prompt(payload)

        response = bedrock.invoke_model(
            body=prompt,
            modelId=model_id,
            accept="application/json",
            contentType="application/json",
        )

        # Parse the response
        response_body = json.loads(response.get("body").read())
        comment = response_body["content"][0]["text"]

        print(f"Generated comment: {comment}")

        try:
            table.delete_item(Key={"id": "latest"})
        except Exception as e:
            print(f"Error deleting item from DynamoDB: {e}")

        try:
            table.put_item(
                Item={"id": "latest",
                      "comment": comment,
                      "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                      }
            )
        except Exception as e:
            print(f"Error writing item from DynamoDB: {e}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            "Succesfully processed {} events".format(len(event["Records"]))
        ),
    }
