# Earnings Comparison Tool

A web application for comparing ASCAP and BMI earnings reports.

## Local Development

To run the application locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python3 app.py
```

Visit `http://localhost:5000` in your browser.

## Important Notes

- The application is configured to handle file uploads up to 300MB
- The server timeout is set to 600 seconds to handle large file processing
- The uploads directory is configured with persistent disk storage

## Features

- Upload and compare ASCAP and BMI earnings reports
- Fuzzy matching for show names and episodes
- Detailed Excel report with:
  - Show-by-show comparison
  - Episode matching
  - Revenue analysis
  - Charts and graphs
