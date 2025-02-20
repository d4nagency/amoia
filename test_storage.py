from google.cloud import storage
import os

def test_gcs_connection():
    print("Testing Google Cloud Storage connection...")
    
    # Initialize the client
    storage_client = storage.Client()
    
    # Get our bucket
    bucket_name = "amoiabucket"
    bucket = storage_client.bucket(bucket_name)
    
    # Test file upload
    test_content = "This is a test file"
    blob = bucket.blob("test.txt")
    blob.upload_from_string(test_content)
    print(f"Successfully uploaded test.txt to {bucket_name}")
    
    # Test file download
    downloaded_content = blob.download_as_string().decode("utf-8")
    print(f"Downloaded content: {downloaded_content}")
    
    # Test file deletion
    blob.delete()
    print("Successfully deleted test.txt")
    
    # List all files in bucket
    print("\nFiles in bucket:")
    blobs = bucket.list_blobs()
    for blob in blobs:
        print(f"- {blob.name}")

if __name__ == "__main__":
    test_gcs_connection()
