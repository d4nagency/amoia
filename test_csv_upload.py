from google.cloud import storage
import os
from google.cloud.storage.blob import Blob
from google.cloud.storage.retry import DEFAULT_RETRY

def test_csv_upload():
    print("Testing CSV file upload...")
    
    # Initialize the client
    storage_client = storage.Client()
    bucket_name = "amoiabucket"
    bucket = storage_client.bucket(bucket_name)
    
    # Custom retry strategy with longer timeout
    custom_retry = DEFAULT_RETRY.with_deadline(120)  # 2 minute timeout
    
    # Upload ASCAP CSV
    ascap_file = "ASCAP 4TH 2023.csv"
    if os.path.exists(ascap_file):
        print(f"Uploading {ascap_file}...")
        blob = bucket.blob(f"uploads/{ascap_file}")
        
        # Get file size before upload
        file_size = os.path.getsize(ascap_file)
        size_mb = file_size / (1024 * 1024)
        print(f"File size to upload: {size_mb:.2f} MB")
        
        # Upload with custom retry strategy
        blob.upload_from_filename(
            ascap_file,
            retry=custom_retry,
            timeout=120  # 2 minute timeout
        )
        print(f"Successfully uploaded {ascap_file}")
        
        # Generate a signed URL (valid for 10 minutes)
        url = blob.generate_signed_url(
            version="v4",
            expiration=600,
            method="GET"
        )
        print(f"Signed URL (valid for 10 minutes): {url}")
    else:
        print(f"File {ascap_file} not found")
    
    # List all files in bucket
    print("\nFiles in bucket:")
    blobs = bucket.list_blobs()
    for blob in blobs:
        print(f"- {blob.name} ({blob.size / (1024 * 1024):.2f} MB)")

if __name__ == "__main__":
    test_csv_upload()
