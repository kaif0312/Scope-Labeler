# Scope Builder - PDF Annotation Tool

A Flask web application for annotating PDF documents with scope information.

## Project Structure

```
Evaluation System APP/
├── app.py                  # Main application entry point
├── config.py               # Configuration settings
├── models/                 # Data models
│   ├── __init__.py
│   ├── user.py             # User management
│   ├── project.py          # Project management
│   └── pdf_processor.py    # PDF processing and annotation
├── routes/                 # Route handlers
│   ├── __init__.py
│   ├── auth.py             # Authentication routes
│   ├── project.py          # Project management routes
│   ├── pdf.py              # PDF processing routes
│   └── admin.py            # Admin dashboard routes
├── static/                 # Static assets
│   ├── css/                # CSS styles
│   │   ├── main.css        # Common styles
│   │   ├── login.css       # Login page styles
│   │   ├── projects.css    # Projects page styles
│   │   └── ...             # Other CSS files
│   └── js/                 # JavaScript files
│       ├── projects.js     # Projects page scripts
│       ├── project_view.js # Project view scripts
│       └── ...             # Other JS files
├── templates/              # HTML templates (currently using template_string)
├── uploads/                # Uploaded PDFs and metadata
├── thumbnails/             # PDF thumbnails
├── annotated_data/         # Annotation data
├── projects/               # Project data
└── users/                  # User data
```

## Requirements

- Python 3.8+
- Flask
- pdf2image
- ultralytics (YOLO)
- Azure Computer Vision API
- Other dependencies listed in requirements.txt

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set environment variables:
   ```
   export AZURE_VISION_ENDPOINT="your_azure_endpoint"
   export AZURE_VISION_KEY="your_azure_key"
   export YOLO_WEIGHTS="path_to_yolo_weights"
   ```

## Running the Application

```
python app.py
```

The application will be available at http://localhost:5000

## Default Login

- Username: admin
- Password: admin

## Features

- User management with admin and worker roles
- Project management for organizing PDFs
- Multi-page PDF support with sheet selection
- YOLO-based figure detection
- OCR using Azure Computer Vision
- Annotation with scopes and bid items
- Auto-tagging based on previous annotations
- Admin dashboard with statistics 