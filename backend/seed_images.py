from pathlib import Path
import boto3
from config import settings

ASSETS_DIR = Path.home() / "Desktop" / "dish_images"

s3_client = boto3.client(
    "s3",
    endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
    aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
    region_name="auto",
)

def upload_seed_images():
    if not ASSETS_DIR.exists():
        print(f"Error: Directory {ASSETS_DIR} does not exist.")
        return

    for image_path in ASSETS_DIR.glob("*.jpg"):
        object_key = f"dishes/{image_path.name}"
        print(f"Uploading {image_path.name} to R2 -> {object_key}...")
        
        with open(image_path, "rb") as file_data:
            s3_client.put_object(
                Bucket=settings.r2_bucket_name,
                Key=object_key,
                Body=file_data,
                ContentType="image/jpeg",
            )
            
    print("All seed images uploaded to Cloudflare R2 successfully!")

if __name__ == "__main__":
    upload_seed_images()