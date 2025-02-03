from flask import Flask, request, render_template, jsonify, send_file
import os
from compare_earnings import compare_earnings
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
# Increase maximum file size to 200MB to handle both files
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size
# Configure maximum request body size
app.config['MAX_CONTENT_PATH'] = None
# Configure request timeout
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Add ProxyFix middleware to handle larger requests
app.wsgi_app = ProxyFix(app.wsgi_app)

# Ensure upload directory exists
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
        
        # Save files
        ascap_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(ascap_file.filename))
        bmi_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(bmi_file.filename))
        
        ascap_file.save(ascap_path)
        bmi_file.save(bmi_path)
        
        try:
            # Run comparison
            report_path = compare_earnings(ascap_path, bmi_path)
            
            if not report_path or not os.path.exists(report_path):
                raise Exception("Failed to generate report")
                
            # Clean up uploaded files
            os.remove(ascap_path)
            os.remove(bmi_path)
            
            # Send the report file
            return send_file(
                report_path, 
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='earnings_comparison_report.xlsx'
            )
            
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
