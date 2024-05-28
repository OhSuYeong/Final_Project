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
