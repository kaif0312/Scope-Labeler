# Scope Builder Application

A modular Flask web application for PDF annotation with features including:
- PDF upload and processing
- YOLO object detection to identify figures
- Azure OCR for text recognition
- Annotation of text regions with scope information
- Admin dashboard for monitoring and management

## Setup Instructions

### Prerequisites
- Python 3.8
- poppler-utils (for pdf2image)

### Installation

1. Clone this repository
```bash
git clone https://github.com/yourusername/scope-builder.git
cd scope-builder
```

2. Create a Python 3.8 virtual environment
```bash
python3.8 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r "Evaluation System APP/minimal_requirements.txt"
```

4. Install YOLO (optional, only if you need object detection)
```bash
pip install ultralytics==8.0.6
```

### Configuration
The application uses configuration settings in `Evaluation_System_APP/config.py`. You'll need to set up:
- Azure OCR API key and endpoint (if using OCR)
- YOLO weights file path (if using object detection)
- Folder paths for uploads, thumbnails, and annotations

### Running the Application
```bash
python app.py
```

The application will be available at http://localhost:5000

### Deploying on Replit (Free)

You can quickly test this application on Replit without using local disk space:

1. Create a free account on [Replit](https://replit.com)
2. Click "Create Repl" and select "Import from GitHub"
3. Enter your GitHub repository URL
4. Once imported, Replit will automatically set up the environment
5. In the Shell, run:
   ```bash
   pip install -r "Evaluation System APP/minimal_requirements.txt"
   python app.py
   ```
6. Replit will provide a URL where your application is hosted

The `.replit` file in the repository configures Replit to use Python 3.8 and sets the correct entry point.

## Project Structure
- `Evaluation_System_APP/` - Main application package
  - `models/` - Data models and processing logic
  - `routes/` - Route handlers for different app features
  - `static/` - CSS, JavaScript, and other static files
  - `templates/` - HTML templates
  - `config.py` - Application configuration
- `app.py` - Application entry point 