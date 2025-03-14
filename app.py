from flask import Flask, request, render_template, jsonify, send_file
import os
import json
from compare_earnings import compare_earnings
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from google.cloud import storage
from config import *
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Google Cloud Storage client with credentials from environment variable
try:
    credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if credentials_json:
        logger.info("Using credentials from environment variable")
        credentials_info = json.loads(credentials_json)
        storage_client = storage.Client.from_service_account_info(credentials_info)
    else:
        logger.info("Using default credentials")
        storage_client = storage.Client()
    bucket = storage_client.bucket(GOOGLE_CLOUD_STORAGE_BUCKET)
except Exception as e:
    logger.error(f"Error initializing Google Cloud Storage: {str(e)}")
    raise

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config')
app.wsgi_app = ProxyFix(app.wsgi_app)

# Ensure upload directory exists for temporary files
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        if 'ascap' not in request.files or 'bmi' not in request.files:
            return jsonify({'error': 'Both ASCAP and BMI files are required'}), 400
        
        ascap_file = request.files['ascap']
        bmi_file = request.files['bmi']
        
        if ascap_file.filename == '' or bmi_file.filename == '':
            return jsonify({'error': 'No selected files'}), 400

        # Validate file sizes before processing
        max_size = app.config['MAX_CONTENT_LENGTH']
        if request.content_length > max_size:
            return jsonify({'error': f'Total upload size exceeds {max_size // (1024*1024)}MB limit'}), 413
        
        logger.info(f"Processing files: ASCAP={ascap_file.filename}, BMI={bmi_file.filename}")
        
        try:
            # Create temporary files with .csv extension
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_ascap:
                ascap_file.save(temp_ascap.name)
                # Upload to Google Cloud Storage with chunked transfer
                blob = bucket.blob(f'uploads/{secure_filename(ascap_file.filename)}')
                blob.chunk_size = 5 * 1024 * 1024  # 5MB chunks
                blob.upload_from_filename(temp_ascap.name)
                ascap_path = temp_ascap.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_bmi:
                bmi_file.save(temp_bmi.name)
                # Upload to Google Cloud Storage with chunked transfer
                blob = bucket.blob(f'uploads/{secure_filename(bmi_file.filename)}')
                blob.chunk_size = 5 * 1024 * 1024  # 5MB chunks
                blob.upload_from_filename(temp_bmi.name)
                bmi_path = temp_bmi.name
            
            logger.info("Running comparison...")
            # Run comparison
            report_path = compare_earnings(ascap_path, bmi_path)
            
            if not report_path or not os.path.exists(report_path):
                raise Exception("Failed to generate report")
            
            logger.info(f"Report generated: {report_path}")
            
            # Upload report to Google Cloud Storage
            report_blob = bucket.blob(f'reports/{os.path.basename(report_path)}')
            report_blob.upload_from_filename(report_path)
            
            # Clean up temporary files
            os.unlink(ascap_path)
            os.unlink(bmi_path)
            os.unlink(report_path)
            
            # Generate signed URL for report download
            url = report_blob.generate_signed_url(
                version="v4",
                expiration=300,  # URL expires in 5 minutes
                method="GET"
            )
            
            logger.info("Processing complete")
            return jsonify({
                'success': True,
                'report_url': url
            })
            
        except Exception as e:
            logger.error(f"Error during file processing: {str(e)}")
            # Clean up files in case of error
            for file_path in [ascap_path, bmi_path]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            raise e
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large'}), 413

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug)
