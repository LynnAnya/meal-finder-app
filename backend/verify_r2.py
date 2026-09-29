"""
Quick script to verify Cloudflare R2 credentials (S3-compatible)
"""

from io import BytesIO
from botocore.exceptions import BotoCoreError, ClientError
from config import settings
from image_utils import _get_s3_client

def verify_r2_connection():
    s3 = _get_s3_client()
    print(f"Bucket: {settings.r2_bucket_name}")
    print(f"Endpoint: {settings.r2_endpoint_url}")
    print()

    test_key = "profile_pics/test.txt"

    # do test upload here
    try:
        s3.upload_fileobj(
            BytesIO(b"test"),
            settings.r2_bucket_name,
            test_key,
            ExtraArgs={"ContentType": "text/plain"},

        )
        print("Upload: SUCCESS")
    except (BotoCoreError, ClientError) as e:
        print(f"Upload: FAILED - {e}")
        return

    # test delete 
    try:
        s3.delete_object(Bucket=settings.r2_bucket_name, Key=test_key)
        print("Delete: SUCCESS!")
    except (BotoCoreError, ClientError) as e:
        print(f"Delete: FAILED - {e}")
        return

    print()
    print("All tests passed! Your R2 configuration is working.")


if __name__ == "__main__":
    verify_r2_connection()