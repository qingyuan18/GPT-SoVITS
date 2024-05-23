####  调用SageMaker endpoint 封装接口 #########
import uuid
import boto3
import os
from datetime import datetime
import json
runtime_sm_client = boto3.client(service_name="sagemaker-runtime")

class ModelClient:
    sagemaker_endpoint = ""
    def __init__(self, model_id):
        self.model_id = model_id
        self.dynamodb = boto3.resource('dynamodb')
        self.s3 = boto3.client('s3')

    def get_bucket_and_key(self,s3uri):
        pos = s3uri.find('/', 5)
        bucket = s3uri[5 : pos]
        key = s3uri[pos + 1 : ]
        return bucket, key


    def set_endpoint(self, sagemaker_endpoint):
        self.sagemaker_endpoint = sagemaker_endpoint

    def invoke_endpoint(self,request:str):
       content_type = "application/json"
       request_body = request
       payload = json.dumps(request_body)
       print(payload)
       response = runtime_sm_client.invoke_endpoint(
           EndpointName=endpointName,
           ContentType=content_type,
           Body=payload,
       )
       result = response['Body'].read().decode()
       print('返回：',result)



    def download_wav_from_s3(s3_path):
        s3 = boto3.resource('s3')
        bucket_name, key = get_bucket_and_key(s3_path)
        localPath = "/tmp/"+os.path.basename(key)
        try:
            s3.Bucket(bucket_name).download_file(key, localPath)
            return localPath
        except ClientError as e:
            print(e)
            return None
