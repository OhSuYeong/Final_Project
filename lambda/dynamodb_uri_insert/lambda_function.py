import boto3
import json

dynamodb_client = boto3.client('dynamodb')

def lambda_handler(event, context):
    # DynamoDB에서 URI 정보 업데이트
    dynamodb_id = event['dynamodb_id']
    bucket_name = event['bucket_name']

    s3_bucket_uri = f"s3://{bucket_name}"

    response = dynamodb_client.update_item(
        TableName='user',
        Key={'userId': {'S': dynamodb_id}},
        UpdateExpression='SET s3_bucket_uri = :val',
        ExpressionAttributeValues={':val': {'S': s3_bucket_uri}}
    )
    print(f"S3 bucket URL {s3_bucket_uri} saved to DynamoDB.")

    return {
        'statusCode': 200,
        'body': json.dumps('URI information updated successfully.')
    }

