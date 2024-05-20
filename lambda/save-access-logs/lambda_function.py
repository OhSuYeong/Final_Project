import boto3
import gzip
import json
from datetime import datetime
from io import BytesIO

def remove_quotes(input_string):
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
        return response.get('StorageClass', 'STANDARD')
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
    
    for item in response.get('Contents', []):
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
                
                if (record['eventName'] == 'GetObject' and 'response-content-disposition' not in record['requestParameters']) or record['eventName'] == 'PutObject':
                    try:
                        response = table.get_item(
                            Key={'entity_tag_value': entity_tag_value}
                        )
                        item = response.get('Item')
                        
                        if item:
                            try:
                                # 수정된 부분: 객체가 실제로 존재하지 않으면 DynamoDB에서 해당 아이템 삭제
                                s3.head_object(Bucket=user_bucket, Key=object_key)
                            except s3.exceptions.ClientError as e:
                                if e.response['Error']['Code'] == '404':
                                    table.delete_item(Key={'entity_tag_value': entity_tag_value})
                                    print(f"Deleted item for non-existing object: {object_key}")
                                else:
                                    raise  # 다른 종류의 예외는 다시 발생시킴

                            current_count = item.get('count', 0)
                            new_count = current_count + 1
                            table.update_item(
                                Key={'entity_tag_value': entity_tag_value},
                                UpdateExpression='SET event_time = :val1, #count_field = :count_value, storage_class = :storage_class',
                                ExpressionAttributeNames={'#count_field': 'count'},
                                ExpressionAttributeValues={':val1': event_time, ':count_value': new_count, ':storage_class': storage_class}
                            )
                        else:
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
                        print(f"Error processing item for {object_key}: {e}")
                else:
                    print(f"Skipping event with unsupported eventName: {record['eventName']}")
                    continue
    
    return {
        'statusCode': 200,
        'body': json.dumps('Data processing complete')
    }
