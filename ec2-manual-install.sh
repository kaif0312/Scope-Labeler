#!/bin/bash

# Manual Installation Script for EC2
# Copy this script to your EC2 instance and run it if you prefer a manual installation

# Set variables
ECR_REPO="982081086086.dkr.ecr.us-east-1.amazonaws.com"
IMAGE_NAME="scopebuilder"
TAG="latest"
AWS_REGION="us-east-1"
APP_PORT=9090

echo "🚀 Starting Scope Builder installation..."

# Install Docker if not already installed
if ! command -v docker &> /dev/null; then
  echo "🔧 Installing Docker..."
  sudo apt-get update
  sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
  sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-compose
  sudo systemctl enable docker
  sudo systemctl start docker
  sudo usermod -aG docker $USER
  echo "✅ Docker installed! You may need to log out and log back in for group changes to take effect."
  echo "After logging back in, run this script again."
  exit 0
fi

# Install AWS CLI if not already installed
if ! command -v aws &> /dev/null; then
  echo "🔧 Installing AWS CLI..."
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
  unzip awscliv2.zip
  sudo ./aws/install
  rm -rf aws awscliv2.zip
  echo "✅ AWS CLI installed!"
fi

# Create directories for volumes
echo "📁 Creating directories for Docker volumes..."
mkdir -p ./scopebuilder/uploads
mkdir -p ./scopebuilder/thumbnails
mkdir -p ./scopebuilder/annotated_data
mkdir -p ./scopebuilder/projects
mkdir -p ./scopebuilder/users
mkdir -p ./scopebuilder/flask_session
echo "✅ Directories created!"

# Login to ECR
echo "🔑 Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

if [ $? -ne 0 ]; then
  echo "❌ ECR login failed. Make sure your instance has the right IAM permissions."
  echo "You can manually run: aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO"
  exit 1
fi

echo "✅ Successfully logged in to ECR!"

# Pull the Docker image
echo "📥 Pulling Scope Builder image from ECR..."
docker pull $ECR_REPO/$IMAGE_NAME:$TAG

if [ $? -ne 0 ]; then
  echo "❌ Failed to pull image. Check your IAM permissions."
  exit 1
fi

echo "✅ Image pulled successfully!"

# Stop and remove existing container if it exists
if docker ps -a | grep -q scopebuilder; then
  echo "🛑 Stopping and removing existing Scope Builder container..."
  docker stop scopebuilder
  docker rm scopebuilder
fi

# Run the container
echo "🚀 Starting Scope Builder container..."
docker run -d --name scopebuilder -p $APP_PORT:$APP_PORT \
  -v $PWD/scopebuilder/uploads:/app/Evaluation_System_APP/uploads \
  -v $PWD/scopebuilder/thumbnails:/app/Evaluation_System_APP/thumbnails \
  -v $PWD/scopebuilder/annotated_data:/app/Evaluation_System_APP/annotated_data \
  -v $PWD/scopebuilder/projects:/app/Evaluation_System_APP/projects \
  -v $PWD/scopebuilder/users:/app/Evaluation_System_APP/users \
  -v $PWD/scopebuilder/flask_session:/app/flask_session \
  -e "FLASK_ENV=production" \
  -e "SECRET_KEY=scopebuilder_secret_key" \
  -e "HOST=0.0.0.0" \
  -e "PORT=$APP_PORT" \
  --restart always \
  $ECR_REPO/$IMAGE_NAME:$TAG

# Verify the container is running
if docker ps | grep -q scopebuilder; then
  PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
  echo "✅ Scope Builder is now running!"
  echo "📊 View container logs with: docker logs scopebuilder"
  echo "🖥️ Access the application at: http://$PUBLIC_IP:$APP_PORT"
  echo "🔄 To restart the container: docker restart scopebuilder"
  echo "🛑 To stop the container: docker stop scopebuilder"
else
  echo "❌ Failed to start container. Check logs with: docker logs scopebuilder"
  exit 1
fi
