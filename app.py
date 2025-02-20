from flask import Flask, request, render_template, jsonify, send_file
import os
import json
from compare_earnings import compare_earnings
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from google.cloud import storage
from config import *
import tempfile

# Initialize Google Cloud Storage client with credentials from environment variable
credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
if credentials_json:
    credentials_info = json.loads(credentials_json)
    storage_client = storage.Client.from_service_account_info(credentials_info)
else:
    storage_client = storage.Client()
bucket = storage_client.bucket(GOOGLE_CLOUD_STORAGE_BUCKET)

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
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as temp_ascap:
            ascap_file.save(temp_ascap.name)
            # Upload to Google Cloud Storage
            blob = bucket.blob(f'uploads/{secure_filename(ascap_file.filename)}')
            blob.upload_from_filename(temp_ascap.name)
            ascap_path = temp_ascap.name

        with tempfile.NamedTemporaryFile(delete=False) as temp_bmi:
            bmi_file.save(temp_bmi.name)
            # Upload to Google Cloud Storage
            blob = bucket.blob(f'uploads/{secure_filename(bmi_file.filename)}')
            blob.upload_from_filename(temp_bmi.name)
            bmi_path = temp_bmi.name
        
        try:
            # Run comparison
            report_path = compare_earnings(ascap_path, bmi_path)
            
            if not report_path or not os.path.exists(report_path):
                raise Exception("Failed to generate report")
            
            # Upload report to Google Cloud Storage
            report_blob = bucket.blob(f'reports/{os.path.basename(report_path)}')
            report_blob.upload_from_filename(report_path)
            
            # Clean up temporary files
            os.unlink(ascap_path)
            os.unlink(bmi_path)
            
            # Generate signed URL for report download
            url = report_blob.generate_signed_url(
                version="v4",
                expiration=300,  # URL expires in 5 minutes
                method="GET"
            )
            
            return jsonify({
                'success': True,
                'report_url': url
            })
            
        except Exception as e:
            # Clean up files in case of error
            for file_path in [ascap_path, bmi_path]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            raise e
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
