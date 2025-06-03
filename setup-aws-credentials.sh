#!/bin/bash

# Script to help set up AWS credentials

echo "🔑 AWS Credentials Setup"
echo "-----------------------"
echo "This script will help you set up your AWS credentials."
echo ""

# Determine where to store credentials
read -p "Do you want to store credentials in environment variables or AWS config file? (env/file): " STORAGE_TYPE

case $STORAGE_TYPE in
  env|ENV)
    echo "Setting up environment variables..."
    read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
    read -p "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
    read -p "Do you have a session token? (y/n): " HAS_TOKEN
    
    if [[ $HAS_TOKEN == "y" ]]; then
      read -p "AWS Session Token: " AWS_SESSION_TOKEN
      echo "export AWS_SESSION_TOKEN=\"$AWS_SESSION_TOKEN\"" 
    fi
    
    echo ""
    echo "Run these commands to set your AWS credentials:"
    echo "export AWS_ACCESS_KEY_ID=\"$AWS_ACCESS_KEY_ID\""
    echo "export AWS_SECRET_ACCESS_KEY=\"$AWS_SECRET_ACCESS_KEY\""
    if [[ $HAS_TOKEN == "y" ]]; then
      echo "export AWS_SESSION_TOKEN=\"$AWS_SESSION_TOKEN\""
    fi
    echo "export AWS_REGION=\"us-east-1\""
    ;;
  
  file|FILE)
    echo "Setting up AWS config file..."
    read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
    read -p "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
    read -p "Do you have a session token? (y/n): " HAS_TOKEN
    
    if [[ $HAS_TOKEN == "y" ]]; then
      read -p "AWS Session Token: " AWS_SESSION_TOKEN
    fi
    
    # Ensure AWS directory exists
    mkdir -p ~/.aws
    
    # Write credentials file
    echo "[default]" > ~/.aws/credentials
    echo "aws_access_key_id = $AWS_ACCESS_KEY_ID" >> ~/.aws/credentials
    echo "aws_secret_access_key = $AWS_SECRET_ACCESS_KEY" >> ~/.aws/credentials
    if [[ $HAS_TOKEN == "y" ]]; then
      echo "aws_session_token = $AWS_SESSION_TOKEN" >> ~/.aws/credentials
    fi
    
    # Write config file
    echo "[default]" > ~/.aws/config
    echo "region = us-east-1" >> ~/.aws/config
    echo "output = json" >> ~/.aws/config
    
    echo ""
    echo "AWS credentials stored in ~/.aws/credentials"
    ;;
    
  *)
    echo "Invalid option. Please choose 'env' or 'file'."
    exit 1
    ;;
esac

echo ""
echo "To verify your AWS credentials, run:"
echo "aws sts get-caller-identity"
