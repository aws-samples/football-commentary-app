import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
# get table name from the environmetn variable
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name)

def handler(event, context):
    message_history_request = table.get_item(Key={'id': 'latest'})
    if 'Item' in message_history_request:
        messages = message_history_request['Item']['comment']
        last_comment = messages[-1]['content'][0]['text']
    else:
        last_comment = 'No data available'

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        #'body': json.dumps(response.get('Item', {}).get('comment', 'No data available'))
        'body': json.dumps(last_comment)
    }
