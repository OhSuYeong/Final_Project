# 1️⃣DynamoDB 이벤트에 따른 S3 bucket 생성 트리거

## 시나리오 과정

회원 가입 시 회원 정보가 DynamoDB에 올라가고 이는 DynamoDB 스트림 기능을 통해 트리거가 발생하여 Lambda를 호출한다. Lambda는 DynamoDB에서 새로 생성된 회원 정보를 토대로 S3 bucket을 자동으로 생성한다.

## 구성 과정

1. DynamoDB에 테이블 생성

![1](https://github.com/OhSuYeong/Final_Project/assets/101083171/816d88e4-794a-4f04-b1cc-f27e14d3f6e4)


여기서 테이블 이름은 USER-DB, 파티션 키는 id(문자열)로 설정하였다.

테이블 설정은 기본 설정

2. DynamoDB 스트림 설정

![2](https://github.com/OhSuYeong/Final_Project/assets/101083171/e88e1fed-b183-426c-b981-60ded2116592)

![3](https://github.com/OhSuYeong/Final_Project/assets/101083171/fc9b3ec7-a5eb-4f56-b94e-bfb83b8f1fdc)



3. Lambda 함수 생성 및 설

![4](https://github.com/OhSuYeong/Final_Project/assets/101083171/56ef465f-809e-48c6-9a4e-fc041bce3752)


함수 이름은 bucket-creation, 런타임은 Python 3.12로 설정

기본 실행 역할 변경에서 기존 역할 사용으로 lambda-role-s3 사용

해당 역할의 권한 정책은 AdministratorAccess와 AmazonS3FullAccess

4. 트리거 추가

![5](https://github.com/OhSuYeong/Final_Project/assets/101083171/85f7e60e-6b6c-409f-80f0-21e043332c79)


소스 선택은 DynamoDB, table은 미리 만든 USER-DB 선택

![6](https://github.com/OhSuYeong/Final_Project/assets/101083171/3502b05f-f261-427d-9a6a-c373df764734)


5. Lambda 함수 코드 작성 후 Deploy

```python
import boto3
import json
from datetime import datetime

# S3 클라이언트 설정
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    # 이벤트로부터 발생한 레코드들을 처리
    for record in event['Records']:
        # INSERT 또는 MODIFY 이벤트만 처리
        if record['eventName'] in ('INSERT', 'MODIFY'):
            # DynamoDB 레코드의 'id' 속성을 가져옴
            dynamodb_id = record['dynamodb']['Keys']['id']['S']
            
            # 현재 타임스탬프를 사용하여 유니크한 버킷 이름 생성
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            bucket_name = f"{dynamodb_id}-{timestamp}"

            # S3 버킷 생성
            try:
                # 'ap-northeast-1' 리전이 아닌 경우
                response = s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': 'ap-northeast-1'
                    }
                )
                print(f"Bucket {bucket_name} created successfully.")
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

```

6. 테스트
- 항목 생성

![7](https://github.com/OhSuYeong/Final_Project/assets/101083171/ab9a61a0-6c56-4f74-98a3-c3ba431b3ca7)


- 트리거 체크

![8](https://github.com/OhSuYeong/Final_Project/assets/101083171/b265b2b6-3a4a-448b-a37f-fa78e2c98d66)


- s3 bucket 생성 확인

![9](https://github.com/OhSuYeong/Final_Project/assets/101083171/40962075-ee5f-47a5-b768-96b1f8efe524)

---

# 2️⃣생성된 USER bucket URI 정보 DynamoDB에 저장
- 참고
    - URI 형식 : [https://s3.[region이름].amazonaws.com/](https://s3.ap-northeast-1.amazonaws.com/backup-frontend-s3)[bucket이름]
        
        ex) https://s3.ap-northeast-1.amazonaws.com/backup-frontend-s3
        
    
    ![1](https://github.com/OhSuYeong/Final_Project/assets/101083171/d8dc9d06-b44b-4131-9f40-30c0e1a25962)

    
    S3 Bucket에 파일/폴더 업로드 했을 때, 해당 파일&폴더의 URL/URI 형식
    
    URI → s3://test-kjs/kjs/
    
    URL → https://test-kjs.s3.ap-northeast-1.amazonaws.com/kjs/
    
    버킷 정책
    
    ```json
    {
        "Version": "2012-10-17",
        "Id": "Policy1714438750165",
        "Statement": [
            {
                "Sid": "Stmt1714438733278",
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "s3:GetBucketLocation",
                    "s3:ListBucket"
                ],
                "Resource": "arn:aws:s3:::test-kjs"
            }
        ]
    }
    ```
    
    CORS
    
    ```json
    [
        {
            "AllowedHeaders": [
                "*"
            ],
            "AllowedMethods": [
                "GET",
                "HEAD",
                "POST"
            ],
            "AllowedOrigins": [
                "*"
            ],
            "ExposeHeaders": [
                "x-amz-server-side-encryption",
                "x-amz-request-id",
                "x-amz-id-2"
            ],
            "MaxAgeSeconds": 3000
        }
    ]
    ```

### **첫 번째 Lambda 함수에서 두 번째 Lambda 함수 호출 추가하기**

1. **Lambda 함수 호출 코드 추가**:

첫 번째 Lambda 함수의 코드에 AWS SDK를 사용하여 두 번째 Lambda 함수를 호출하는 코드를 추가합니다.

- event
    
    ```json
    {
    'Records': 
    [
    {'eventID': '951d1bdaf472892066ed6534d30169a0', 
    'eventName': 'INSERT', 'eventVersion': '1.1', 
    'eventSource': 'aws:dynamodb', 
    'awsRegion': 'ap-northeast-1', 
    'dynamodb': {
    'ApproximateCreationDateTime': 1714458435.0, 
    'Keys': {'id': {'S': 'test5'}}, 
    'NewImage': {'id': {'S': 'test5'}}, 
    'SequenceNumber': '146700000000063054215432', 
    'SizeBytes': 14, 'StreamViewType': 'NEW_AND_OLD_IMAGES'}, 
    'eventSourceARN': 'arn:aws:dynamodb:ap-northeast-1:243795305209:table/USER-DB/stream/2024-04-30T06:03:31.491'
    }
    ]
    }
    ```
    

```python
import boto3
import json
from datetime import datetime

# AWS 클라이언트 설정
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    # print(f'event ----> {event}')
    for record in event['Records']:
        if record['eventName'] in ('INSERT'):
            dynamodb_id = record['dynamodb']['Keys']['userId']['S']
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            bucket_name = f"siu{dynamodb_id}-{timestamp}"

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
```

1. **두 번째 Lambda 함수 수정**:

두 번째 Lambda 함수 **`bucket_uri_insert`**에서는 받은 인자를 활용하여 DynamoDB에 URI 정보를 업데이트하는 코드를 작성합니다

- event
    
    ```json
    {'dynamodb_id': 'test4', 'bucket_name': 'test4-20240430054427'}
    ```
    

```python
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

```

위의 코드는 첫 번째 Lambda 함수에서 S3 버킷 생성 후에 두 번째 Lambda 함수를 비동기적으로 호출하고, 두 번째 Lambda 함수에서는 받은 인자를 사용하여 DynamoDB에 URI 정보를 업데이트하는 과정을 보여줍니다.

---

# 3️⃣각 객체 별 액세스 log 분석 후 빈도, 최근 접속 일시, storageclass db 저장

<포맷>

### **ALB Access Log Format**

**[type] [time] [elb] [client:port] [target:port] [request_processing_time] [target_processing_time] [response_processing_time] [elb_status_code] [target_status_code] [received_bytes] [sent_bytes] ["request"] ["user_agent"] [ssl_cipher] [ssl_protocol] [target_group_arn] ["trace_id"] ["domain_name"] ["chosen_cert_arn"] [matched_rule_priority] [request_creation_time] ["actions_executed"] ["redirect_url"] ["error_reason"] ["target:port_list"] ["target_status_code_list"] ["classification"] ["classification_reason"]**

## CloudTrail을 이용한 bucket에 저장된 file access log 지정 bucket에 저장

1. CloudTrail에서 추적 생성
![1](https://github.com/OhSuYeong/Final_Project/assets/101083171/f14813c6-6d9e-4e64-9920-253d34d48070)
2. 추적 속성 선택
- 추적 이름 : **s3-bucketfile-accesslog**
- 스토리지 위치 :
- 로그 파일 SSE-KMS 암호화 : 비활성화
- 로그 파일 검증 : 비활성화
- SNS 알림 전송 : 비활성화
- CloudWatch Logs : 비활성
3. 로그 이벤트 선택
- 데이터 이벤트 : S3
- 필드 : eventName - equals - GetObject
- 필드 : eventName - equals - PutObject
- 필드 : resources:ARN - startsWith - arn:aws:s3:::siu-
4. 생성
![2](https://github.com/OhSuYeong/Final_Project/assets/101083171/bd7a11b9-a57c-42aa-b645-faaf185d51ad)
5. 테스트
- siu- 로 시작하는 bucket의 파일을 업로드 또는 다운로드 실행
- log 저장 bucket에서 확인
![3](https://github.com/OhSuYeong/Final_Project/assets/101083171/995b26af-1736-48b5-b785-1c9160a12d76)
- 저장된 log file은 JSON 형태

dynamodb에 저장되는 형태 (주기 : 매월 28일에 DB 업데이트)

| entity_tag_value (문자열) | bucket_name | count | event_time | storage_class |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |
|  |  |  |  |  |

**event parameter**

- bucket name → bucketName
- 파일명 → key
- 최근 접속 일시 → eventTime

lambda function code(save-access-logs)

```python
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

    lambda_client = boto3.client('lambda')

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

                if (record['eventName'] == 'GetObject' and 'response-content-disposition' in record['requestParameters']) or record['eventName'] == 'PutObject':
                    try:
                        response = table.get_item(
                            Key={'entity_tag_value': entity_tag_value}
                        )
                        item = response.get('Item')

                        if item:
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
    
    # 첫 번째 함수 실행 완료 후에 두 번째 Lambda 함수 호출
    try:
        response = lambda_client.invoke(
            FunctionName='update-access-logs',  # 두 번째 Lambda 함수 이름
            InvocationType='RequestResponse',  # 동기 호출 설정
        )
        print(f"Second Lambda function invoked with response: {response}")
    except Exception as e:
        print(f"Error invoking second Lambda function: {e}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Data processing complete')
    }

```

lambda function code(update-access-logs)

```python

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

```

### 결과
![4](https://github.com/OhSuYeong/Final_Project/assets/101083171/37fea177-525a-49fd-a314-82f86c19104c)

## <EventBridge 를 이용한 Cronjob 설정>

### 매월 28일 00:00 에 한달동안 쌓인 로그 DynamoDB에 저장

1) 이름 : save_access_log 로 지정
![5](https://github.com/OhSuYeong/Final_Project/assets/101083171/6753173e-d833-4487-92fe-12a00baf6ec4)
2) cronjob 패턴 설정 **( 패턴 : 0 0 28 * ? * )**
![6](https://github.com/OhSuYeong/Final_Project/assets/101083171/b86e64c3-a8ce-4150-b0af-e28099a9c82d)
3) 대상 API 로 AWS Lambda 선택
![7](https://github.com/OhSuYeong/Final_Project/assets/101083171/4d652f47-d33a-4e5d-a063-4fd8164888e6)
4) Invoke(함수 호출) 선택 → save-access-logs 함수 실행하도록 설정
![8](https://github.com/OhSuYeong/Final_Project/assets/101083171/ad6d4056-cf79-4344-922a-d8c7ab512fd2)

**<최종 결과>**

**save_access_log → 매월 28일에 액세스 로그 저장(save-access-logs 함수 실행)**

**(패턴 : 0 0 28 * ? *)**

**update_storage_class → 매월 1일에 스토리지 변경(update-storage-class 함수 실행)**

**(패턴 : 0 0 1 * ? *)**
![9](https://github.com/OhSuYeong/Final_Project/assets/101083171/a5112ae7-3f4a-4fd3-a383-d3017c73323d)

---

# 4️⃣최근 접속 일시로 스토리지 클래스 결정 로직 및 람다 생성

- 참고자료
    
    S3 Glacier Flexible Retrieval에 저장된 객체의 스토리지 클래스를 S3 Glacier Deep Archive가 아닌 스토리지 클래스로 변경하려면 먼저 복원 작업을 사용하여 객체의 임시 복사본을 만들어야 합니다. 그런 다음 복사 작업을 통해 S3 Standard, S3 Intelligent-Tiering, S3 Standard-IA, S3 One Zone-IA 또는 Reduced Redundancy를 스토리지 클래스로 지정하여 객체를 덮어씁니다.
    
    Amazon S3 콘솔의 **복사** 작업은 S3 Glacier Flexible Retrieval 또는 S3 Glacier Deep Archive 스토리지 클래스의 복원된 객체에 대해 지원되지 않습니다. 이러한 복원된 객체를 복사하려면 AWS Command Line Interface(AWS CLI), AWS SDK 또는 Amazon S3 REST API를 사용합니다.
    
    https://docs.aws.amazon.com/ko_kr/AmazonS3/latest/userguide/copy-object.html
    
    https://docs.aws.amazon.com/ko_kr/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html#before-deciding-to-archive-objects
    
    수명 주기 규칙을 통한 방법으로 Storageclass level을 낮추는 방법도 존재
    
    - **put_bucket_lifecycle_configuration 메서드 사용**
    - 해당 방식은 빈도 수를 통한 변경 방식에 적용 불가능하므로 배제

## Storage Class별 방법 분류

|  | Standard | Standard-IA | Glacier |
| --- | --- | --- | --- |
| Standard | - | copy_object method | 복원 후 copy_object method |
| Standard-IA | copy_object method | - | - |
| Glacier | copy_object method | copy_object method | - |

lambda_function.py (update-storage-class)

```python
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

def get_storage_class(days_difference):  # storage class 결정 함수
    if days_difference <= 30:
        return 'STANDARD'
    elif days_difference <= 90:
        return 'STANDARD_IA'
    else :
        return 'GLACIER'

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

        # 동일한 스토리지 클래스로 변경하지 않음
        if current_storage_class == new_storage_class:
            print(f"Skipping {entity_tag_value} as it is already in the correct storage class {new_storage_class}.")
            continue

        # 스토리지 클래스 변경 허용 조건 추가
        valid_transition = False
        if (current_storage_class in ['STANDARD', 'STANDARD_IA'] and new_storage_class in ['STANDARD', 'STANDARD_IA']) or \
           (current_storage_class == 'STANDARD_IA' and new_storage_class == 'GLACIER'):
            valid_transition = True

        if not valid_transition:
            print(f"Skipping {entity_tag_value} due to invalid storage class transition from {current_storage_class} to {new_storage_class}.")
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

```

EventBridge 설정
![1](https://github.com/OhSuYeong/Final_Project/assets/101083171/75aee157-6a9d-4258-8e04-ef0d69c88461)

## 스토리지 클래스 변경

1) STANDARD/STANDARD-IA → GLACIER 변경하는 경우

→ 문제없음. (update-storage-class 함수 실행)

2) GLACIER → STANDARD/STANDARD-IA 변경하는 경우

→ 복원 후 copy 필요함.

---

# 5️⃣접속 빈도로 스토리지 클래스 결정 로직 및 람다 생성

lambda_function.py (update-storage-class-freq)

```python
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

```

### 결과
![1](https://github.com/OhSuYeong/Final_Project/assets/101083171/9dd5c7bf-1851-41b6-8fce-65205921db21)
![2](https://github.com/OhSuYeong/Final_Project/assets/101083171/825ed219-9952-4bc4-a73d-a6107a907fde)

---

# 6️⃣Glacier→Standard 복원 및 Storageclass 변환 기능 구현

## Glacier → Standard 기능 구현

**시나리오 및 기능 구현**

1. 복원 요청 button 클릭 : 해당 lambda 함수 호출
2. 복원 요청 → 복원 중으로 바뀜 : 이후 로그인 혹은 새로고침 시에는 S3.client에서 복원 중인지 확인 후에 복원 중 button이 표시되도록 구현
3. 복원 완료 시에는 lambda에서 자동으로 copy method를 이용하여 storageclass가 변경되어 있을 것이므로 버튼 표시 X, 객체 정보 화면 표시는 원래 객체 화면 표시와 동일하게 구현

https://docs.aws.amazon.com/ko_kr/AmazonS3/latest/userguide/restoring-objects.html#restore-archived-objects-status

1. **AWS Step Functions**를 사용하여 복원 작업을 관리.
2. **S3 이벤트 알림**을 사용하여 복원 완료 시 Lambda 함수를 트리거.

**Lambda 함수 1 - 복원 요청**

**S3 이벤트 알림 설정**

1. **S3 버킷에서 이벤트 알림 설정**:
    - S3 콘솔에서 버킷의 "Properties" 탭을 클릭합니다.
    - "Event notifications" 섹션에서 "Create event notification"을 클릭합니다.
    - "All object restore completed" 이벤트를 선택하고 Lambda 함수를 트리거하도록 설정합니다.

lambda_function(Restore-storageclass-update)

```python
import boto3
import urllib.parse

s3 = boto3.client('s3')

def lambda_handler(event, context):
    print(event)
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # 객체 키를 디코딩하고 '+'를 공백으로 치환합니다.
    decoded_key = urllib.parse.unquote(key).replace('+', ' ')
    print(f'Decoded key: {decoded_key}')
    
    try:
        # 객체의 복원 상태를 확인합니다.
        response = s3.head_object(Bucket=bucket, Key=decoded_key)
        
        if 'Restore' in response and 'ongoing-request="false"' in response['Restore']:
            # 복원이 완료되었으면 스토리지 클래스를 변경합니다.
            copy_source = {'Bucket': bucket, 'Key': decoded_key}
            s3.copy_object(
                Bucket=bucket,
                Key=decoded_key,
                CopySource=copy_source,
                StorageClass='STANDARD',
                MetadataDirective='COPY'
            )
            print(f'Storage class of {decoded_key} changed to STANDARD')
            
            # 객체의 태그를 제거합니다.
            s3.delete_object_tagging(Bucket=bucket, Key=decoded_key)
        else:
            print(f'Restore is not completed yet for {decoded_key}')
    
    except s3.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            print(f'Object {decoded_key} not found in bucket {bucket}')
        elif error_code == '404':
            print(f'404 error for object {decoded_key} in bucket {bucket}')
        else:
            print(f'ClientError occurred: {e}')
    except Exception as e:
        print(f'Unexpected error occurred: {e}')

```

### **결과**

<복원 전>
![1](https://github.com/OhSuYeong/Final_Project/assets/101083171/ce7ad768-415f-4722-ac29-a969b66ceea8)
![2](https://github.com/OhSuYeong/Final_Project/assets/101083171/2578deef-7d0e-4bbe-8fe9-dd41f20ef562)

<복원 후>
![3](https://github.com/OhSuYeong/Final_Project/assets/101083171/313afcb2-51a6-4f43-9e7e-e9ebfe150347)
![4](https://github.com/OhSuYeong/Final_Project/assets/101083171/b7d56e40-aba7-4917-b300-da3000d9ef93)

bucket-creation 수정

```python
import boto3
import json
from datetime import datetime
import uuid

# AWS 클라이언트 설정
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

def configure_s3_bucket_notification(bucket_name):
    lambda_name = 'Restore-storageclass-update'
    lambda_arn = 'arn:aws:lambda:ap-northeast-1:243795305209:function:Restore-storageclass-update'
    
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
```

### 결과
![5](https://github.com/OhSuYeong/Final_Project/assets/101083171/290b33f4-86be-48a8-815c-57beaa5049db)

## Restore-object-request

### [lambda 함수]

```python
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # 객체의 스토리지 클래스를 확인합니다.
    response = s3.head_object(Bucket=bucket, Key=key)
    storage_class = response['StorageClass']
    
    if storage_class == 'GLACIER':
        # 객체가 Glacier 스토리지 클래스에 있는 경우 복원을 요청합니다.
        s3.restore_object(
            Bucket=bucket,
            Key=key,
            RestoreRequest={'Days': 1, 'GlacierJobParameters': {'Tier': 'Standard'}}
        )
        print(f'Restore request initiated for {key}')
        
        # 객체에 복원 요청을 나타내는 태그를 추가합니다.
        s3.put_object_tagging(
            Bucket=bucket,
            Key=key,
            Tagging={
                'TagSet': [
                    {
                        'Key': 'RestoreRequested',
                        'Value': 'true'
                    }
                ]
            }
        )
    else:
        print(f'Object {key} is not in GLACIER storage class')

```

### [테스트]

Event JSON 파일(백엔드와 맞춰서 변경 필요할 수도)

```python
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "awsRegion": "xx-northeast-x",
      "eventTime": "2024-05-24T12:46:45.123Z",
      "eventName": "ObjectCreated:Put",
      "userIdentity": {
        "principalId": "EXAMPLE"
      },
      "requestParameters": {
        "sourceIPAddress": "1.2.3.4"
      },
      "responseElements": {
        "x-amz-request-id": "EXAMPLE123456789",
        "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "testConfigRule",
        "bucket": {
          "name": "siuu5237866e-9d52-4ee1-95aa-4d97b671ab98-20240524044227",
          "ownerIdentity": {
            "principalId": "EXAMPLE"
          },
          "arn": "arn:aws:s3:::your-bucket-name"
        },
        "object": {
          "key": "yrestore_object_request.py",
          "size": 1024,
          "eTag": "05d4b63d383d864a77e24dd88bb3f2bf",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    }
  ]
}
```

lambda 함수 실행 결과 → 복원 진행됨
<img width="1167" alt="6" src="https://github.com/OhSuYeong/Final_Project/assets/101083171/a9aba11e-f264-46ae-9f3e-8deb4d170960">
