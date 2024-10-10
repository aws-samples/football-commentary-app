import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
# get table name from the environmetn variable
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name)


def handler(event, context):
    response = table.get_item(Key={'id': 'latest'})

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        #'body': json.dumps(response.get('Item', {}).get('comment', 'No data available'))
        'body': json.dumps(response['Item'])
    }
