# 1️⃣DynamoDB 이벤트에 따른 S3 bucket 생성 트리거

## 시나리오 과정

회원 가입 시 회원 정보가 DynamoDB에 올라가고 이는 DynamoDB 스트림 기능을 통해 트리거가 발생하여 Lambda를 호출한다. Lambda는 DynamoDB에서 새로 생성된 회원 정보를 토대로 S3 bucket을 자동으로 생성한다.

## 구성 과정

1. DynamoDB에 테이블 생성

![1](https://github.com/OhSuYeong/Final_Project/assets/101083171/816d88e4-794a-4f04-b1cc-f27e14d3f6e4)


여기서 테이블 이름은 USER-DB, 파티션 키는 id(문자열)로 설정하였다.

테이블 설정은 기본 설정

1. DynamoDB 스트림 설정

![2](https://github.com/OhSuYeong/Final_Project/assets/101083171/e88e1fed-b183-426c-b981-60ded2116592)

![3](https://github.com/OhSuYeong/Final_Project/assets/101083171/fc9b3ec7-a5eb-4f56-b94e-bfb83b8f1fdc)



1. Lambda 함수 생성 및 설

![4](https://github.com/OhSuYeong/Final_Project/assets/101083171/56ef465f-809e-48c6-9a4e-fc041bce3752)


함수 이름은 bucket-creation, 런타임은 Python 3.12로 설정

기본 실행 역할 변경에서 기존 역할 사용으로 lambda-role-s3 사용

해당 역할의 권한 정책은 AdministratorAccess와 AmazonS3FullAccess

1. 트리거 추가

![5](https://github.com/OhSuYeong/Final_Project/assets/101083171/85f7e60e-6b6c-409f-80f0-21e043332c79)


소스 선택은 DynamoDB, table은 미리 만든 USER-DB 선택

![6](https://github.com/OhSuYeong/Final_Project/assets/101083171/3502b05f-f261-427d-9a6a-c373df764734)


1. Lambda 함수 코드 작성 후 Deploy

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

1. 테스트
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
        
    
    [Amazon S3에서 퍼블릭 액세스 차단을 비활성화 했음에도 AccessDenied이 뜨는 경우 해결 방법은? | DevelopersIO](https://dev.classmethod.jp/articles/if-access-denied-appears-even-though-you-disabled-public-access-blocking-on-amazon-s3-what-is-the-workaround/)
    
    [https://velog.io/@ygreenb/AWS-S3-정책-권한-설정-시-403-에러](https://velog.io/@ygreenb/AWS-S3-%EC%A0%95%EC%B1%85-%EA%B6%8C%ED%95%9C-%EC%84%A4%EC%A0%95-%EC%8B%9C-403-%EC%97%90%EB%9F%AC)
    
    ![Untitled](https://prod-files-secure.s3.us-west-2.amazonaws.com/1d1f5e17-6d94-451c-9271-c698ee060384/5c41eb25-62a7-4be4-a16e-ff43abc8b777/Untitled.png)
    
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
    
    [URL 접근 예시]
    
    ![Untitled](https://prod-files-secure.s3.us-west-2.amazonaws.com/1d1f5e17-6d94-451c-9271-c698ee060384/dfffeeee-bd16-400d-8d35-2470a5c65b1f/Untitled.png)
    
    ![Untitled](https://prod-files-secure.s3.us-west-2.amazonaws.com/1d1f5e17-6d94-451c-9271-c698ee060384/dfffeeee-bd16-400d-8d35-2470a5c65b1f/Untitled.png)
    

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
