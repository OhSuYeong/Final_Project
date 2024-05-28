import boto3
import json
from datetime import datetime
import os
import uuid

# AWS 클라이언트 설정
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

def configure_s3_bucket_notification(bucket_name):
    # 현재 실행 중인 Lambda 함수의 ARN과 이름을 가져옴
    lambda_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
    lambda_region = os.environ['AWS_REGION']
    lambda_account_id = boto3.client('sts').get_caller_identity().get('Account')
    lambda_arn = f'arn:aws:lambda:{lambda_region}:{lambda_account_id}:function:{lambda_name}'
    
    # 고유한 StatementId 생성
    statement_id = str(uuid.uuid4())
    
    # Lambda 권한 추가
    s3_arn = f'arn:aws:s3:::{bucket_name}'
    try:
        response = lambda_client.add_permission(
            FunctionName=lambda_name,
            StatementId=statement_id,  # 고유한 Id 사용
            Action='lambda:InvokeFunction',
            Principal='s3.amazonaws.com',
            SourceArn=s3_arn
        )
        print("Lambda permission response:", response)
    except lambda_client.exceptions.ResourceConflictException as e:
        print("Permission already exists, skipping add_permission.")
    
    # 알림 구성 생성
    notification_configuration = {
        'LambdaFunctionConfigurations': [
            {
                'LambdaFunctionArn': lambda_arn,
                'Events': ['s3:ObjectRestore:Completed']
            }
        ]
    }
   
    # 버킷 알림 설정
    response = s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration=notification_configuration
    )
   
    return response

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
                
                # 버킷 생성 완료 대기
                waiter = s3_client.get_waiter('bucket_exists')
                waiter.wait(Bucket=bucket_name)
                
                response_config = configure_s3_bucket_notification(bucket_name)
                
                print(response_config)

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