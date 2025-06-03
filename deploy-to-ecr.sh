#!/bin/bash

# Deploy Scope Builder to AWS ECR
# This script builds the Docker image, tags it, and pushes it to ECR

# AWS Region
AWS_REGION="us-east-1"
# ECR Repository
ECR_REPO="982081086086.dkr.ecr.us-east-1.amazonaws.com"
# Image name
IMAGE_NAME="scopebuilder"
# Tag
TAG="latest"

echo "🚀 Starting deployment to AWS ECR..."

# Step 0: Check AWS credentials
echo "🔑 Checking AWS credentials..."
AWS_IDENTITY=$(aws sts get-caller-identity 2>&1)
if [ $? -ne 0 ]; then
  echo "❌ AWS credential check failed: $AWS_IDENTITY"
  echo "Please run ./setup-aws-credentials.sh to configure your AWS credentials."
  echo "Common issues:"
  echo "  - Expired temporary credentials"
  echo "  - Missing or incorrect AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
  echo "  - Missing AWS_SESSION_TOKEN (if using temporary credentials)"
  exit 1
fi

echo "✅ Using AWS identity: $AWS_IDENTITY"

# Step 1: Check if the ECR repository exists
echo "🔍 Checking ECR repository..."
ECR_CHECK=$(aws ecr describe-repositories --repository-names $IMAGE_NAME --region $AWS_REGION 2>&1)
if [ $? -ne 0 ]; then
  if echo "$ECR_CHECK" | grep -q "RepositoryNotFoundException"; then
    echo "⚠️  Repository not found. Creating it now..."
    aws ecr create-repository --repository-name $IMAGE_NAME --region $AWS_REGION
    if [ $? -ne 0 ]; then
      echo "❌ Failed to create ECR repository. Please check your permissions."
      exit 1
    fi
    echo "✅ Repository created: $ECR_REPO/$IMAGE_NAME"
  else
    echo "❌ Error checking ECR repository: $ECR_CHECK"
    exit 1
  fi
fi

# Step 2: Authenticate with AWS ECR
echo "🔐 Authenticating with AWS ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

if [ $? -ne 0 ]; then
  echo "❌ Authentication failed. Please check your AWS credentials and try again."
  exit 1
fi

# Check if Docker is installed and running
echo "🐳 Checking Docker installation..."
if ! command -v docker &> /dev/null; then
  echo "❌ Docker is not installed. Please install Docker and try again."
  exit 1
fi

# Check if Docker daemon is running
docker info &> /dev/null
if [ $? -ne 0 ]; then
  echo "❌ Docker daemon is not running. Please start Docker and try again."
  exit 1
fi
echo "✅ Docker is running properly."

# Step 3: Build the Docker image for AMD64 platform (for EC2 compatibility)
echo "🔨 Building Docker image for AMD64 platform..."

# Check if buildx is installed and set up
if ! docker buildx version &> /dev/null; then
  echo "Setting up Docker buildx for multi-architecture builds..."
  docker buildx create --name multiarch --use
fi

# Build the image for AMD64 platform and load it into Docker
docker buildx build --platform linux/amd64 -t $IMAGE_NAME --load .

if [ $? -ne 0 ]; then
  echo "❌ Docker build failed."
  echo "If you're on ARM-based Mac (M1/M2/M3), make sure Docker Desktop is running with Rosetta enabled."
  exit 1
fi

echo "✅ Built image for AMD64 platform successfully."

# Step 3: Tag the image for ECR
echo "🏷️  Tagging image for ECR..."
docker tag $IMAGE_NAME:$TAG $ECR_REPO/$IMAGE_NAME:$TAG

if [ $? -ne 0 ]; then
  echo "❌ Tagging failed."
  exit 1
fi

# Step 4: Push to ECR
echo "📤 Pushing image to ECR..."
docker push $ECR_REPO/$IMAGE_NAME:$TAG

if [ $? -ne 0 ]; then
  echo "❌ Push to ECR failed."
  exit 1
fi

echo "✅ Successfully deployed $IMAGE_NAME:$TAG to AWS ECR!"
echo "🔗 Image URI: $ECR_REPO/$IMAGE_NAME:$TAG"
echo ""
echo "To deploy this image on your EC2 instance, use the following commands:"
echo "---------------------------------------------------------------"
echo "ssh your-ec2-instance"
echo "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO"
echo "docker pull $ECR_REPO/$IMAGE_NAME:$TAG"
echo "docker run -d --name scopebuilder -p 9090:9090 \\"
echo "  -v ./uploads:/app/Evaluation_System_APP/uploads \\"
echo "  -v ./thumbnails:/app/Evaluation_System_APP/thumbnails \\"
echo "  -v ./annotated_data:/app/Evaluation_System_APP/annotated_data \\"
echo "  -v ./projects:/app/Evaluation_System_APP/projects \\"
echo "  -v ./users:/app/Evaluation_System_APP/users \\"
echo "  -v ./flask_session:/app/flask_session \\"
echo "  $ECR_REPO/$IMAGE_NAME:$TAG"
echo "---------------------------------------------------------------"
