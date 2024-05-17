import boto3
import gzip
import json
from datetime import datetime
from io import BytesIO

def remove_quotes(input_string):
    # 큰 따옴표를 제거하여 반환
    return input_string.replace('"', '')

def get_entity_tag_value(s3_client, bucket_name, object_key):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        entity_tags = remove_quotes(response['ETag'])
        
        if entity_tags:
            return entity_tags
        else:
            return None
    except Exception as e:
        print(f"Error getting entity tag for {object_key}: {e}")
        return None

def get_storage_class(s3_client, bucket_name, object_key):
    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        return response.get('StorageClass', 'STANDARD')  # 기본값을 'STANDARD'로 설정
    except Exception as e:
        print(f"Error getting storage class for {object_key}: {e}")
        return None

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('file_access')
    bucket_name = 'aws-cloudtrail-logs-243795305209-72226aca'
    now = datetime.utcnow()
    year_month = now.strftime('%Y/%m')
    prefix = f'AWSLogs/243795305209/CloudTrail/ap-northeast-1/{year_month}'
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    
    for item in response['Contents']:
        key = item['Key']
        obj = s3.get_object(Bucket=bucket_name, Key=key)

        with gzip.GzipFile(fileobj=BytesIO(obj['Body'].read())) as gzipfile:
            file_content = gzipfile.read()
            log_data = json.loads(file_content.decode('utf-8'))

            for record in log_data['Records']:
                object_key = record['requestParameters']['key']
                user_bucket = record['requestParameters']['bucketName']
                entity_tag_value = get_entity_tag_value(s3, user_bucket, object_key)
                storage_class = get_storage_class(s3, user_bucket, object_key)
                event_time = record['eventTime']
                
                if record['eventName'] == 'PutObject':
                    # DynamoDB에 저장
                    if entity_tag_value:
                        table.put_item(
                            Item={
                                'entity_tag_value': entity_tag_value,
                                'bucket_name': user_bucket,
                                'event_time': event_time,
                                'storage_class': storage_class,
                                'count': 1
                            }
                        )
                    else:
                        print(f"Failed to get entity_tag_value for object: {object_key}")
                elif record['eventName'] == 'GetObject' and 'response-content-disposition' not in record['requestParameters']:
                    # DynamoDB에서 엔터티 태그 값으로 아이템 가져오기
                    try:
                        response = table.get_item(
                            Key={'entity_tag_value': entity_tag_value}
                        )
                        item = response.get('Item')
                        
                        if item:
                            # 아이템이 있으면 count 필드를 업데이트
                            current_count = item.get('count', 0)
                            new_count = current_count + 1
                            # event_time 및 count 필드 업데이트
                            table.update_item(
                                Key={'entity_tag_value': entity_tag_value},
                                UpdateExpression='SET event_time = :val1, #count_field = :count_value, storage_class = :storage_class',
                                ExpressionAttributeNames={'#count_field': 'count'},
                                ExpressionAttributeValues={':val1': event_time, ':count_value': new_count, ':storage_class': storage_class}
                            )
                        else:
                            # 아이템이 없으면 새로운 아이템 생성
                            table.put_item(
                                Item={
                                    'entity_tag_value': entity_tag_value,
                                    'bucket_name': user_bucket,
                                    'event_time': event_time,
                                    'storage_class': storage_class,
                                    'count': 1
                                }
                            )
                    except Exception as e:
                        print(f"Error getting item from DynamoDB: {e}")
                else:
                    print(f"Skipping event with unsupported eventName: {record['eventName']}")
                    continue
    
    return {
        'statusCode': 200,
        'body': json.dumps('Data processing complete')
    }
