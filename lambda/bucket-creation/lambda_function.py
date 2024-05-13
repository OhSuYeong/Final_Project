import boto3
import json
from datetime import datetime

# AWS 클라이언트 설정
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    #print(f'event ----> {event}')
    for record in event['Records']:
        if record['eventName'] in ('INSERT'):
            dynamodb_id = record['dynamodb']['Keys']['userId']['S']
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            bucket_name = f"siuu{dynamodb_id}-{timestamp}"

            try:
                response = s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': 'ap-northeast-1'
                    }
                )
                print(f"Bucket {bucket_name} created successfully.")

                # 두 번째 Lambda 함수 호출
                invoke_response = lambda_client.invoke(
                    FunctionName='dynamodb_uri_insert',  # 두 번째 Lambda 함수 이름
                    InvocationType='Event',  # 비동기 호출 설정
                    Payload=json.dumps({'dynamodb_id': dynamodb_id, 'bucket_name': bucket_name})
                )
                print(f"Second Lambda function invoked with response: {invoke_response}")

            except s3_client.exceptions.BucketAlreadyExists as e:
                print(f"Error: Bucket {bucket_name} already exists.")
            except s3_client.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                print(f"Error: {error_code}, Message: {error_message}")

    return {
        'statusCode': 200,
        'body': json.dumps('Lambda function executed successfully.')
    }
