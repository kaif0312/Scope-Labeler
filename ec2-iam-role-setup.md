# Setting Up IAM Role for EC2 Instance

For enhanced security, it's recommended to use IAM roles for EC2 instances instead of hardcoded credentials or even AWS configure. This document explains how to set up an IAM role for your EC2 instance to access ECR.

## Benefits

- No need to store credentials on the EC2 instance
- Credentials are automatically rotated
- More secure than using access keys
- Follows AWS best practices

## Steps to Create and Attach an IAM Role

1. **Create an IAM Role**

   a. Open the AWS Management Console and navigate to the IAM service
   
   b. Click on "Roles" in the left navigation pane
   
   c. Click "Create role"
   
   d. Select "AWS service" as the trusted entity type
   
   e. Select "EC2" as the AWS service
   
   f. Click "Next"
   
   g. In the permissions page, search for and attach the following policies:
      - `AmazonECR-ReadOnly` (for pulling images only)
      - Or create a custom policy using the `ecr-pull-policy.json` file in this repo
   
   h. Click "Next"
   
   i. Enter a name for the role (e.g., "EC2-ECR-Pull-Role")
   
   j. Add any tags if desired
   
   k. Click "Create role"

2. **Attach the Role to Your EC2 Instance**

   a. Go to the EC2 service in the AWS Management Console
   
   b. Select your instance
   
   c. Click "Actions" > "Security" > "Modify IAM role"
   
   d. Select the role you created
   
   e. Click "Update IAM role"

3. **Verify Access from the EC2 Instance**

   After attaching the role, the EC2 instance will automatically be able to access ECR without any explicit credentials. Run this command on your EC2 instance to verify:
   
   ```bash
   aws ecr describe-repositories --region us-east-1
   ```

## Using with the Deployment Script

Once you have the IAM role set up, you can use the `deploy-from-ecr-to-ec2.sh` script without worrying about passing AWS credentials. The AWS CLI on the EC2 instance will automatically use the credentials provided by the instance's IAM role.

This is the most secure approach for deploying from ECR to EC2.
