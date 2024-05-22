
import json
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('file_access')

    try:
        # 1. DynamoDB 에서 모든 Bucket name 가져오기
        response = table.scan(ProjectionExpression="bucket_name")
        bucket_names = set(item['bucket_name'] for item in response['Items'])
        for bucket_name in bucket_names:
            # 2. S3 버킷에서 모든 객체의 ETag 가져오기
            s3_etags = []
            try:
                paginator = s3.get_paginator('list_objects_v2')  # 수정된 부분
                page_iterator = paginator.paginate(Bucket=bucket_name)

                for page in page_iterator:
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            try:
                                response = s3.head_object(Bucket=bucket_name, Key=obj['Key'])
                                etag = response['ETag'].strip('"')
                                s3_etags.append(etag)
                            except ClientError as e:
                                print(f"{bucket_name} 에서 {obj['Key']} 의 ETag를 불러오는 데에 실패하였습니다 : {e.response['Error']['Message']}")
                                continue
            except ClientError as e:
                print(f"{bucket_name} 의 ETag 불러오는 데에 실패하였습니다 : {e.response['Error']['Message']}")
                continue
            
            # 3. DynamoDB 에서 해당 버킷의 ETag 목록 가져오기
            try:
                response = table.scan(
                    FilterExpression=Attr('bucket_name').eq(bucket_name),
                    ProjectionExpression="entity_tag_value"
                )
                dynamodb_etags = [item['entity_tag_value'] for item in response['Items']]
            except ClientError as e:
                print(f"{bucket_name} 의 DynamoDB 스캔에 실패하였습니다 : {e.response['Error']['Message']}")
                continue

            # 4. S3에 없는 ETag에 해당하는 DynamoDB 항목 삭제하기
            for etag in dynamodb_etags:
                if etag not in s3_etags:
                    try:
                        response = table.delete_item(
                            Key={
                                'entity_tag_value': etag,
                            }
                        )
                        print(f"{bucket_name} 에서 ETag 가 {etag} 인 항목이 삭제되었습니다.")
                    except ClientError as e:
                        print(f"{bucket_name} 의 항목을 삭제하는 데에 오류가 생겼습니다: {e.response['Error']['Message']}")

        return {
            'statusCode': 200,
            'body': json.dumps("Successfully synchronized!!!")
        }
    
    except Exception as e:
        print(f"Error : {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }
