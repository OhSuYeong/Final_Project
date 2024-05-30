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
