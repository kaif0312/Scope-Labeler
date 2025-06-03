FROM python:3.12-slim

# Install system dependencies including poppler for PDF handling and libGL for OpenCV/YOLO
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY Evaluation_System_APP/minimal_requirements.txt .
RUN pip install --no-cache-dir -r minimal_requirements.txt
RUN pip install --no-cache-dir ultralytics==8.3.142 flask-cors flask-session

# Copy the rest of the application
COPY . .

# Create necessary directories that might not exist in the repo
RUN mkdir -p Evaluation_System_APP/uploads \
    Evaluation_System_APP/thumbnails \
    Evaluation_System_APP/annotated_data \
    Evaluation_System_APP/projects \
    Evaluation_System_APP/users \
    flask_session

# Environment variables with defaults
ENV SECRET_KEY="scopebuilder_secret_key" \
    FLASK_APP=app.py \
    FLASK_DEBUG="false" \
    HOST="0.0.0.0" \
    PORT="9090" \
    AZURE_VISION_ENDPOINT="https://scopebuilder.cognitiveservices.azure.com" \
    AZURE_VISION_KEY="75gzAOgClEIGv8CxaYZcre8X04QxJZGE256MK4y7dMaL1sfLtnHdJQQJ99BEACYeBjFXJ3w3AAAFACOGeQxC"

# Expose the port the app runs on
EXPOSE 9090

# Command to run the application
CMD ["python", "app.py"]
