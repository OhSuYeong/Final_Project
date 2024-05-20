import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

def get_storage_class(days_difference):
    if days_difference <= 30:
        return 'STANDARD'
    elif days_difference <= 90:
        return 'STANDARD_IA'
    elif days_difference <= 180:
        return 'GLACIER'
    else:
        return 'DEEP_ARCHIVE'

def get_object_key_by_etag(bucket_name, etag_value):
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

def lambda_handler(event, context):
    # AWS 리소스 초기화
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('file_access')

    # DynamoDB에서 모든 엔터티 태그 값과 해당 정보 가져오기
    response = table.scan()
    items = response['Items']

    for item in items:
        entity_tag_value = item['entity_tag_value']
        bucket_name = item['bucket_name']
        event_time_str = item['event_time']
        current_storage_class = item['storage_class']  # DynamoDB에서 스토리지 클래스 가져오기

        # ISO 8601 형식의 문자열을 datetime 객체로 변환
        event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))

        # 현재 시간(UTC) 가져오기
        current_time_utc = datetime.now(timezone.utc)

        # 현재 시간과의 차이 계산
        time_difference = current_time_utc - event_time
        days_difference = time_difference.days

        # 스토리지 클래스 결정
        new_storage_class = get_storage_class(days_difference)

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

        # Glacier 및 Deep Archive에서의 복원 필요성 처리
        if current_storage_class in ['GLACIER', 'DEEP_ARCHIVE']:
            if new_storage_class not in ['GLACIER', 'DEEP_ARCHIVE']:
                # 복원이 필요한 경우 복원 요청
                try:
                    s3.restore_object(
                        Bucket=bucket_name,
                        Key=object_key,
                        RestoreRequest={'Days': 1, 'GlacierJobParameters': {'Tier': 'Standard'}}
                    )
                    print(f"Restore requested for {object_key} in bucket {bucket_name}.")
                except ClientError as e:
                    print(f"Error restoring object {object_key} in bucket {bucket_name}: {e}")
                # 복원이 진행 중인 경우 스토리지 클래스 변경을 건너뜀
                continue

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
        except ClientError as e:
            print(f"Error copying object {object_key} in bucket {bucket_name}: {e}")

    return {
        'statusCode': 200,
        'body': 'Storage class update initiated for all objects'
    }

