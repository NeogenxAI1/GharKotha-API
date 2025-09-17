import os
import uuid
from datetime import datetime
from pathlib import Path


from urllib.parse import urlparse

import boto3
from botocore.client import Config
from dotenv import load_dotenv

from core.config import settings

ACCOUNT_ID = settings.ACCOUNT_ID
ACCESS_KEY_ID = settings.ACCESS_KEY_ID
SECRET_ACCESS_KEY = settings.SECRET_ACCESS_KEY
BUCKET_NAME = settings.BUCKET_NAME
PUBLIC_BASE_URL = settings.PUBLIC_BASE_URL


def get_unique_name():
    guid_str = str(uuid.uuid4())
    timestamp_int = int(datetime.now().timestamp())
    return f"{guid_str}_{timestamp_int}"

def get_filename_with_extension(image_path):
    parsed_url = urlparse(image_path)
    return Path(parsed_url.path).name

def upload_image_and_get_url(image_path):
    # Create S3 client for R2
    endpoint = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto"
    )

    # Create unique key for object in bucket
    filename = get_filename_with_extension(image_path)
    object_key = f"{get_unique_name()}_{filename}"

    # Upload the image
    with open(image_path, "rb") as f:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=object_key,
            Body=f,
            ACL="public-read",  # optional, for public access
            ContentType="image/png"  # adjust as needed
        )

    # Return public URL
    return f"{PUBLIC_BASE_URL}/{object_key}"
