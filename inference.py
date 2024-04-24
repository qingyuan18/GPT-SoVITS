import uuid
import json
import urllib.request
import urllib.parse
import base64
from pydantic import BaseModel, Field
from PIL import Image
import io
import sys
import boto3
import os
import traceback
import time

WORKING_DIR="/tmp"

def get_bucket_and_key(s3uri):
    """
    get_bucket_and_key is helper function
    """
    pos = s3uri.find('/', 5)
    bucket = s3uri[5: pos]
    key = s3uri[pos + 1:]
    return bucket, key

def write_wav_to_s3(audio_bytes_values,output_s3uri=""):
    """
    write wav to s3 bucket
    """
    s3_client = boto3.client('s3')
    s3_bucket = os.environ.get("s3_bucket", "sagemaker-us-west-2-687912291502")
    prediction ={}
    default_output_s3uri = f's3://{s3_bucket}/gpt_sovits_output/wav/'
    if output_s3uri is None or output_s3uri=="":
        output_s3uri=default_output_s3uri    
    
    bucket, key = get_bucket_and_key(output_s3uri)
    key = f'{key}gpt_sovits_{int(time.time())}.wav'
    file_obj = io.BytesIO(audio_bytes_values)
    s3_client.upload_fileobj(
            Fileobj=file_obj,
            Bucket=bucket,
            Key=key
        )
    print('wav: ', f's3://{bucket}/{key}')
    prediction['result']=f's3://{bucket}/{key}'
    return prediction



class InferenceOpt(BaseModel):
    refer_wav_path: str = "",
    prompt_text: str = "",
    prompt_language:str = "zh",
    text:str = "my queue, my love ,my wife。",
    text_language :str = "zh"
    output_s3uri:str = "s3://sagemaker-us-west-2-687912291502/gpt_sovits_output/wav/"
