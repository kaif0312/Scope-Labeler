#!/bin/bash

# Build AMD64 Docker image for EC2 deployment
# Use this script when building from an ARM-based Mac (M1/M2/M3)

# AWS Region
AWS_REGION="us-east-1"
# ECR Repository
ECR_REPO="982081086086.dkr.ecr.us-east-1.amazonaws.com"
# Image name
IMAGE_NAME="scopebuilder"
# Tag
TAG="latest"

echo "🚀 Starting AMD64 image build for ECR deployment..."

# Check AWS credentials
echo "🔑 Checking AWS credentials..."
AWS_IDENTITY=$(aws sts get-caller-identity 2>&1)
if [ $? -ne 0 ]; then
  echo "❌ AWS credential check failed: $AWS_IDENTITY"
  echo "Please run ./setup-aws-credentials.sh to configure your AWS credentials."
  exit 1
fi

echo "✅ Using AWS identity: $AWS_IDENTITY"

# Authenticate with AWS ECR
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

# Set up buildx for multi-architecture builds
echo "🛠️ Setting up Docker buildx..."
docker buildx version &> /dev/null
if [ $? -ne 0 ]; then
  echo "❌ Docker buildx is not available. Please update Docker Desktop to the latest version."
  exit 1
fi

# Create a new builder instance if it doesn't exist
echo "Creating/using buildx builder..."
docker buildx inspect multiarch &> /dev/null || docker buildx create --name multiarch --use

# Build and push directly to ECR for AMD64 platform
echo "🔨 Building and pushing Docker image for AMD64 platform..."
docker buildx build --platform linux/amd64 \
  -t $ECR_REPO/$IMAGE_NAME:$TAG \
  --push .

if [ $? -ne 0 ]; then
  echo "❌ Build and push failed."
  echo "Common issues:"
  echo "  - Docker Desktop not running in Rosetta mode on M1/M2/M3 Macs"
  echo "  - Insufficient permissions to push to ECR"
  echo "  - Network connectivity issues"
  exit 1
fi

echo "✅ Successfully built and pushed AMD64 image to ECR!"
echo "🔗 Image URI: $ECR_REPO/$IMAGE_NAME:$TAG"
echo ""
echo "To deploy this image on your EC2 instance, run:"
echo "---------------------------------------------------------------"
echo "./deploy-from-ecr-to-ec2.sh [your-ssh-key] [your-ec2-address]"
echo ""
echo "Or if you're already on the EC2 instance, run:"
echo "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO"
echo "docker pull $ECR_REPO/$IMAGE_NAME:$TAG"
echo "docker run -d --name scopebuilder -p 9090:9090 \\"
echo "  -v \$PWD/scopebuilder/uploads:/app/Evaluation_System_APP/uploads \\"
echo "  -v \$PWD/scopebuilder/thumbnails:/app/Evaluation_System_APP/thumbnails \\"
echo "  -v \$PWD/scopebuilder/annotated_data:/app/Evaluation_System_APP/annotated_data \\"
echo "  -v \$PWD/scopebuilder/projects:/app/Evaluation_System_APP/projects \\"
echo "  -v \$PWD/scopebuilder/users:/app/Evaluation_System_APP/users \\"
echo "  -v \$PWD/scopebuilder/flask_session:/app/flask_session \\"
echo "  $ECR_REPO/$IMAGE_NAME:$TAG"
echo "---------------------------------------------------------------"
