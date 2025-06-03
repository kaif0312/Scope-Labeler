#!/bin/bash

# EC2 deployment script for Scope Builder (ECR Image)
# Usage: ./deploy-from-ecr-to-ec2.sh [ssh_key] [ec2_instance_address]
# Example: ./deploy-from-ecr-to-ec2.sh ~/.ssh/my-ec2-key.pem ubuntu@ec2-12-345-67-89.compute-1.amazonaws.com
#
# Note: This script assumes that AWS CLI is properly configured on the EC2 instance
# with the required permissions to pull from ECR.

SSH_KEY=$1
EC2_ADDRESS=$2
AWS_REGION="us-east-1"
ECR_REPO="982081086086.dkr.ecr.us-east-1.amazonaws.com"
IMAGE_NAME="scopebuilder"
TAG="latest"
APP_PORT=9090

# Parameter validation
if [ -z "$SSH_KEY" ] || [ -z "$EC2_ADDRESS" ]; then
  echo "❌ Missing parameters"
  echo "Usage: ./deploy-from-ecr-to-ec2.sh [ssh_key] [ec2_instance_address]"
  echo "Example: ./deploy-from-ecr-to-ec2.sh ~/.ssh/my-ec2-key.pem ubuntu@ec2-12-345-67-89.compute-1.amazonaws.com"
  exit 1
fi

# Check if the SSH key file exists
if [ ! -f "$SSH_KEY" ]; then
  echo "❌ SSH key file '$SSH_KEY' not found"
  exit 1
fi

# Verify EC2 connectivity first
echo "🔑 Verifying SSH connectivity to EC2 instance..."
ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=accept-new $EC2_ADDRESS "echo Connected successfully" &> /dev/null

if [ $? -ne 0 ]; then
  echo "❌ Cannot connect to EC2 instance. Please check your SSH key and instance address."
  exit 1
fi
echo "✅ EC2 connection verified"

echo "Setting up Docker and deploying on EC2..."
ssh -i $SSH_KEY $EC2_ADDRESS << EOF
  # Check if docker is installed
  if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt-get update
    sudo apt-get install -y docker-ce
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker \$(whoami)
    
    # Need to reconnect for group changes to take effect
    echo "Docker installed. Please reconnect to the instance and run the script again."
    exit 0
  fi
  
  # Install AWS CLI if not already installed
  if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
  fi
  
  # Check if AWS CLI is configured
  if ! aws sts get-caller-identity &> /dev/null; then
    echo "AWS CLI is not configured or credentials are invalid."
    echo "Configuring AWS CLI..."
    
    # Create a simple configuration wizard
    echo "Please provide your AWS credentials for ECR access:"
    read -p "AWS Access Key ID: " AWS_ACCESS_KEY
    read -p "AWS Secret Access Key: " AWS_SECRET_KEY
    read -p "Do you need to provide a session token? (y/n): " NEED_TOKEN
    
    # Configure AWS CLI
    aws configure set aws.region $AWS_REGION
    aws configure set aws.access_key_id $AWS_ACCESS_KEY
    aws configure set aws.secret_access_key $AWS_SECRET_KEY
    
    if [[ "$NEED_TOKEN" == "y" ]]; then
      read -p "AWS Session Token: " AWS_SESSION_TOKEN
      aws configure set aws.session_token $AWS_SESSION_TOKEN
    fi
    
    # Verify configuration worked
    if ! aws sts get-caller-identity &> /dev/null; then
      echo "Failed to configure AWS CLI. Please check your credentials and try again."
      exit 1
    fi
    echo "AWS CLI successfully configured."
  else
    echo "AWS CLI is already configured."
  fi
  
  # Login to ECR
  echo "Logging in to ECR..."
  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO
  
  # Create directories for volumes if they don't exist
  echo "Creating directories for Docker volumes..."
  mkdir -p ./scopebuilder/uploads
  mkdir -p ./scopebuilder/thumbnails
  mkdir -p ./scopebuilder/annotated_data
  mkdir -p ./scopebuilder/projects
  mkdir -p ./scopebuilder/users
  mkdir -p ./scopebuilder/flask_session
  
  # Pull the latest image
  echo "Pulling the latest image from ECR..."
  docker pull $ECR_REPO/$IMAGE_NAME:$TAG
  
  # Stop and remove existing container if it exists
  echo "Checking for existing container..."
  if docker ps -a | grep -q scopebuilder; then
    echo "Stopping and removing existing container..."
    docker stop scopebuilder
    docker rm scopebuilder
  fi
  
  # Run the new container
  echo "Starting new container..."
  docker run -d --name scopebuilder -p $APP_PORT:$APP_PORT \\
    -v \$PWD/scopebuilder/uploads:/app/Evaluation_System_APP/uploads \\
    -v \$PWD/scopebuilder/thumbnails:/app/Evaluation_System_APP/thumbnails \\
    -v \$PWD/scopebuilder/annotated_data:/app/Evaluation_System_APP/annotated_data \\
    -v \$PWD/scopebuilder/projects:/app/Evaluation_System_APP/projects \\
    -v \$PWD/scopebuilder/users:/app/Evaluation_System_APP/users \\
    -v \$PWD/scopebuilder/flask_session:/app/flask_session \\
    $ECR_REPO/$IMAGE_NAME:$TAG
    
  # Check if container is running
  if docker ps | grep -q scopebuilder; then
    echo "✅ Container is running successfully!"
    echo "Application is now accessible at http://\$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):$APP_PORT"
  else
    echo "❌ Failed to start container. Check logs with: docker logs scopebuilder"
  fi
EOF

echo "Deployment completed!"
