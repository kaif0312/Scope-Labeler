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

#### Environment Variables (Recommended)
Copy the `.env.template` file to `.env` and customize the values:
```bash
cp .env.template .env
```

Key environment variables you can configure:
- `SECRET_KEY` - Flask application secret key
- `FLASK_ENV` - "development" or "production"
- `HOST` - Host address to bind the server to (default: 0.0.0.0)
- `PORT` - Port to run the application on (default: 9090)
- `AZURE_VISION_ENDPOINT` - Azure Computer Vision API endpoint
- `AZURE_VISION_KEY` - Azure Computer Vision API key
- `YOLO_WEIGHTS` - Path to YOLO model weights file (default: App directory's weights folder)

#### Configuration File
The application also uses configuration settings in `Evaluation_System_APP/config.py`. You may need to adjust:
- Azure OCR API key and endpoint (if using OCR)
- YOLO weights file path (if using object detection)
- Folder paths for uploads, thumbnails, and annotations

### Running the Application

#### Option 1: Direct Python Execution
```bash
python app.py
```

The application will be available at http://localhost:9090

#### Option 2: Using Docker (Recommended for Production)

Docker provides an isolated, consistent environment that works the same way on any system.

1. Build and start the Docker container:
```bash
docker-compose up -d
```

2. Access the application at http://localhost:9090

3. To stop the application:
```bash
docker-compose down
```

### AWS Deployment Options

#### Option 1: Direct EC2 Deployment

This method copies the application code to EC2 and runs it using Docker:

1. Make sure your EC2 instance is running and accessible via SSH
2. Run the deployment script:
```bash
./deploy-ec2.sh /path/to/your-ssh-key.pem ubuntu@your-ec2-address
```

3. The script will install Docker, copy the application, and start it automatically
4. Access the application at http://your-ec2-public-ip:9090

#### Option 2: ECR + EC2 Deployment (Recommended)

This method builds the Docker image locally, pushes it to ECR, and then deploys from ECR to EC2:

1. **Setup AWS Credentials**: Choose one of the following methods:

   a. **Using Temporary Credentials (local development)**:
   ```bash
   # Run the AWS credentials setup script
   ./setup-aws-credentials.sh
   
   # Test your ECR access
   ./test-ecr-access.sh
   ```

   b. **Using IAM Roles (recommended for production)**:
   - Follow the instructions in `ec2-iam-role-setup.md` to set up an IAM role for your EC2 instance
   - This is more secure as it eliminates the need to store credentials on your EC2 instance

2. **Push to ECR**:
   ```bash
   ./deploy-to-ecr.sh
   ```

3. **Deploy from ECR to EC2**:
   ```bash
   # Using the modified script that supports AWS configure on the EC2 instance
   ./deploy-from-ecr-to-ec2.sh /path/to/your-ssh-key.pem ubuntu@your-ec2-address
   ```

4. The script will:
   - Install Docker on EC2 if needed
   - Set up AWS credentials on the EC2 instance if not already configured
   - Pull the image from ECR and start the container
   
5. Access the application at http://your-ec2-public-ip:9090

### AWS Troubleshooting

#### Invalid Security Token
If you encounter an error like `The security token included in the request is invalid`:
- Temporary AWS credentials (including session tokens) typically expire after a few hours
- Run the `setup-aws-credentials.sh` script to configure fresh credentials
- Verify your credentials are working with `aws sts get-caller-identity`

#### ECR Repository Access Issues
- Ensure your IAM user/role has permissions to access ECR
- For EC2 instances, make sure the instance profile has the ECR pull policy attached
- Test ECR authentication with `./test-ecr-access.sh`

#### EC2 IAM Role Requirements

Ensure your EC2 instance has an IAM role with permissions to pull from ECR:

1. Go to AWS IAM console
2. Create a policy using the `ecr-pull-policy.json` file in this repository
3. Attach the policy to your EC2 instance's role

For detailed instructions on setting up and using IAM roles with EC2:
- See `ec2-iam-role-setup.md` in this repository
- This approach eliminates the need for storing AWS credentials on the instance

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