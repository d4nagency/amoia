# Earnings Comparison Tool

A web application for comparing ASCAP and BMI earnings reports.

## Deployment to Render

1. Create a new account on [Render](https://render.com) if you haven't already

2. Create a new Web Service:
   - Go to your Render Dashboard
   - Click "New +" button
   - Select "Web Service"
   - Connect your GitHub repository
   - Choose the Standard plan (needed for large file uploads)

3. Configure the service:
   - Name: earnings-comparison-tool (or your preferred name)
   - Environment: Python 3
   - Region: Choose the closest to your users
   - Branch: main (or your default branch)
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --timeout 300 --workers 3 --max-requests 1 --limit-request-line 0 --limit-request-field_size 0`

4. Set Environment Variables:
   - Add `MAX_UPLOAD_SIZE=200000000` (for 200MB limit)

5. Configure Resources:
   - Choose "Standard" instance type
   - Set disk storage to at least 1GB

6. Click "Create Web Service"

## Important Notes

- The application is configured to handle file uploads up to 200MB
- The server timeout is set to 300 seconds to handle large file processing
- Make sure to select the Standard plan or higher as the free tier won't support large file uploads
- The uploads directory is configured with persistent disk storage

## Local Development

To run the application locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
gunicorn wsgi:app --bind 127.0.0.1:5000 --timeout 300 --workers 3 --max-requests 1 --limit-request-line 0 --limit-request-field_size 0
```

Visit `http://localhost:5000` in your browser.
