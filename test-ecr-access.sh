#!/bin/bash

# Script to test ECR repository access

# AWS Region
AWS_REGION="us-east-1"
# ECR Repository
ECR_REPO="982081086086.dkr.ecr.us-east-1.amazonaws.com"

echo "🔍 Testing AWS ECR Access"
echo "-----------------------"

# Step 1: Check AWS credentials
echo "Testing AWS credentials..."
AWS_IDENTITY=$(aws sts get-caller-identity)
if [ $? -ne 0 ]; then
  echo "❌ AWS credential check failed."
  echo "Please ensure your AWS credentials are valid and have the necessary permissions."
  echo ""
  echo "You can either:"
  echo "1. Run ./setup-aws-credentials.sh to configure temporary credentials, or"
  echo "2. Set up an IAM role for your EC2 instance (see ec2-iam-role-setup.md)"
  exit 1
fi

echo "✅ AWS credential check passed!"
echo "Identity: $AWS_IDENTITY"
echo ""

# Step 2: Test ECR authentication
echo "Testing ECR authentication..."
ECR_LOGIN=$(aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO 2>&1)
if [ $? -ne 0 ]; then
  echo "❌ ECR authentication failed."
  echo "Error: $ECR_LOGIN"
  echo "Make sure your IAM user/role has ECR permissions."
  exit 1
fi

echo "✅ ECR authentication successful!"
echo ""

# Step 3: List ECR repositories
echo "Listing ECR repositories..."
aws ecr describe-repositories --region $AWS_REGION

echo ""
echo "✅ ECR access test completed successfully!"
echo "You can now proceed with the deployment."
