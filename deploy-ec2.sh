#!/bin/bash

# EC2 deployment script for Scope Builder
# Usage: ./deploy-ec2.sh [ssh_key] [ec2_instance_address]
# Example: ./deploy-ec2.sh ~/.ssh/my-ec2-key.pem ec2-user@ec2-12-345-67-89.compute-1.amazonaws.com

SSH_KEY=$1
EC2_ADDRESS=$2

if [ -z "$SSH_KEY" ] || [ -z "$EC2_ADDRESS" ]; then
  echo "Usage: ./deploy-ec2.sh [ssh_key] [ec2_instance_address]"
  exit 1
fi

echo "Packaging the application..."
tar --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' -czf scopebuilder.tar.gz .

echo "Copying files to EC2 instance..."
scp -i $SSH_KEY scopebuilder.tar.gz $EC2_ADDRESS:~/

echo "Setting up Docker and deploying on EC2..."
ssh -i $SSH_KEY $EC2_ADDRESS << 'EOF'
  # Install Docker if not already installed
  if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo yum update -y
    sudo yum install -y docker
    sudo service docker start
    sudo usermod -a -G docker ec2-user
    
    # Need to reconnect for group changes to take effect
    echo "Docker installed. Please reconnect to the instance and run the script again."
    exit 0
  fi
  
  # Install Docker Compose if not already installed
  if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
  fi
  
  # Clean up previous deployment if exists
  if [ -d "~/scopebuilder" ]; then
    echo "Removing previous deployment..."
    rm -rf ~/scopebuilder
  fi
  
  # Extract and deploy
  mkdir -p ~/scopebuilder
  tar -xzf scopebuilder.tar.gz -C ~/scopebuilder
  cd ~/scopebuilder
  
  # Create production .env file if not exists
  if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.template .env
    echo "FLASK_ENV=production" >> .env
  fi
  
  # Build and start the containers
  echo "Building and starting the application..."
  docker-compose build
  docker-compose up -d
  
  echo "Application is now running at http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):9090"
EOF

echo "Cleaning up local files..."
rm scopebuilder.tar.gz

echo "Deployment completed!"
