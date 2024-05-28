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

