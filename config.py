import os

# Google Cloud Storage configuration
GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT', 'amoia-451501')  # Your project ID
GOOGLE_CLOUD_STORAGE_BUCKET = os.getenv('GOOGLE_CLOUD_STORAGE_BUCKET', 'amoiabucket')  # Your bucket name

# Local settings
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 300 * 1024 * 1024  # 300MB max file size

# Flask settings
DEBUG = os.getenv('FLASK_ENV') == 'development'
