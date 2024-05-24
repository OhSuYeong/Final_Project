import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # AWS 리소스 초기화
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('file_access')

    # DynamoDB에서 모든 아이템 가져오기
    response = table.scan()
    items = response['Items']

    # 버킷별로 그룹화
    buckets = {}
    for item in items:
        bucket_name = item['bucket_name']
        if bucket_name not in buckets:
            buckets[bucket_name] = []
        buckets[bucket_name].append(item)
    
    for bucket_name, bucket_items in buckets.items():
        # count 값 기준으로 정렬
        sorted_items = sorted(bucket_items, key=lambda x: x['count'], reverse=True)
        
        total_items = len(sorted_items)
        standard_limit = int(total_items * 0.5)
        # standard_limit까지는 STANDARD, 나머지는 STANDARD_IA로 설정

        for idx, item in enumerate(sorted_items):
            entity_tag_value = item['entity_tag_value']
            current_storage_class = item['storage_class']
            
            # 스토리지 클래스 결정
            if idx < standard_limit:
                new_storage_class = 'STANDARD'
            else:
                new_storage_class = 'STANDARD_IA'

            # 동일한 스토리지 클래스로 변경하지 않음
            if current_storage_class == new_storage_class:
                print(f"Skipping {entity_tag_value} as it is already in the correct storage class {new_storage_class}.")
                continue

            try:
                # DynamoDB에서 해당 객체의 S3 키 가져오기
                object_key = get_object_key_by_etag(bucket_name, entity_tag_value)
                
                if object_key is None:
                    print(f"Object with ETag {entity_tag_value} not found in bucket {bucket_name}. Skipping.")
                    continue

                print(f"Object key: {object_key}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    print(f"Object {entity_tag_value} not found in bucket {bucket_name}. Deleting from DynamoDB.")
                    table.delete_item(Key={'entity_tag_value': entity_tag_value})
                    continue
                else:
                    raise

            # 객체 복사 및 스토리지 클래스 변경
            copy_source = {'Bucket': bucket_name, 'Key': object_key}
            try:
                s3.copy_object(
                    Bucket=bucket_name,
                    CopySource=copy_source,
                    Key=object_key,
                    MetadataDirective='COPY',
                    StorageClass=new_storage_class
                )
                print(f"Storage class for {object_key} in bucket {bucket_name} changed to {new_storage_class}.")

                # DynamoDB의 storage_class 필드 업데이트
                table.update_item(
                    Key={'entity_tag_value': entity_tag_value},
                    UpdateExpression='SET storage_class = :val',
                    ExpressionAttributeValues={':val': new_storage_class}
                )
                print(f"DynamoDB updated for {entity_tag_value} with new storage class {new_storage_class}.")
            except ClientError as e:
                print(f"Error copying object {object_key} in bucket {bucket_name}: {e}")

    return {
        'statusCode': 200,
        'body': 'Storage class update initiated for all objects'
    }

def get_object_key_by_etag(bucket_name, etag_value):  # 해당 object로부터 object_key 가져오는 함수
    s3 = boto3.client('s3')

    continuation_token = None
    while True:
        if continuation_token:
            response = s3.list_objects_v2(Bucket=bucket_name, ContinuationToken=continuation_token)
        else:
            response = s3.list_objects_v2(Bucket=bucket_name)

        if 'Contents' not in response:
            print("버킷에 객체가 없습니다.")
            return None

        for obj in response['Contents']:
            if obj['ETag'].strip('"') == etag_value:
                return obj['Key']

        # 다음 페이지로 이동
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break

    print("해당 ETag 값을 가진 객체를 찾을 수 없습니다.")
    return None

