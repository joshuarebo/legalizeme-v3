#!/bin/bash

# AWS ECS Fargate Deployment Script for Counsel AI Legal Backend
# This script automates the complete deployment process

set -e

# Configuration
REGION="us-east-1"
CLUSTER_NAME="counsel-cluster"
SERVICE_NAME="counsel-service"
TASK_FAMILY="counsel-task"
ECR_REPO_NAME="counsel-ai"
ALB_NAME="counsel-alb"
TARGET_GROUP_NAME="counsel-targets"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting AWS ECS Fargate Deployment for Counsel AI${NC}"

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: ${ACCOUNT_ID}${NC}"

# Step 1: Create ECR Repository
echo -e "${YELLOW}📦 Step 1: Creating ECR Repository...${NC}"
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION
echo -e "${GREEN}✓ ECR Repository ready${NC}"

# Step 2: Build and Push Docker Image
echo -e "${YELLOW}🐳 Step 2: Building and pushing Docker image...${NC}"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

docker build -f Dockerfile.ecs -t $ECR_REPO_NAME .
docker tag $ECR_REPO_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:latest
echo -e "${GREEN}✓ Docker image pushed to ECR${NC}"

# Step 3: Create CloudWatch Log Group
echo -e "${YELLOW}📊 Step 3: Creating CloudWatch Log Group...${NC}"
aws logs describe-log-groups --log-group-name-prefix "/ecs/counsel-task" --region $REGION 2>/dev/null | grep -q "/ecs/counsel-task" || \
aws logs create-log-group --log-group-name "/ecs/counsel-task" --region $REGION
echo -e "${GREEN}✓ CloudWatch Log Group ready${NC}"

# Step 4: Create IAM Roles
echo -e "${YELLOW}🔐 Step 4: Creating IAM Roles...${NC}"

# Task Execution Role
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create execution role if it doesn't exist
aws iam get-role --role-name ecsTaskExecutionRole 2>/dev/null || \
aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Task Role with Bedrock permissions
cat > task-role-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:${REGION}:${ACCOUNT_ID}:parameter/counsel/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam get-role --role-name counsel-task-role 2>/dev/null || \
aws iam create-role --role-name counsel-task-role --assume-role-policy-document file://trust-policy.json

aws iam put-role-policy --role-name counsel-task-role --policy-name CounselTaskPolicy --policy-document file://task-role-policy.json

echo -e "${GREEN}✓ IAM Roles configured${NC}"

# Step 5: Store secrets in Parameter Store
echo -e "${YELLOW}🔑 Step 5: Storing secrets in Parameter Store...${NC}"
echo "Please provide the following credentials:"

read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
read -s -p "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
echo
read -s -p "Secret Key (32+ characters): " SECRET_KEY
echo
read -s -p "Hugging Face Token: " HUGGING_FACE_TOKEN
echo

aws ssm put-parameter --name "/counsel/aws-access-key-id" --value "$AWS_ACCESS_KEY_ID" --type "SecureString" --overwrite
aws ssm put-parameter --name "/counsel/aws-secret-access-key" --value "$AWS_SECRET_ACCESS_KEY" --type "SecureString" --overwrite
aws ssm put-parameter --name "/counsel/secret-key" --value "$SECRET_KEY" --type "SecureString" --overwrite
aws ssm put-parameter --name "/counsel/hugging-face-token" --value "$HUGGING_FACE_TOKEN" --type "SecureString" --overwrite

echo -e "${GREEN}✓ Secrets stored in Parameter Store${NC}"

# Step 6: Create ECS Cluster
echo -e "${YELLOW}🏗️ Step 6: Creating ECS Cluster...${NC}"
aws ecs describe-clusters --clusters $CLUSTER_NAME --region $REGION 2>/dev/null | grep -q "ACTIVE" || \
aws ecs create-cluster --cluster-name $CLUSTER_NAME --capacity-providers FARGATE --region $REGION
echo -e "${GREEN}✓ ECS Cluster ready${NC}"

echo -e "${GREEN}🎉 Deployment preparation complete!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Update aws-ecs-deployment.json with your Account ID: ${ACCOUNT_ID}"
echo -e "2. Create VPC and subnets if needed"
echo -e "3. Create Application Load Balancer"
echo -e "4. Register task definition and create service"

# Cleanup temporary files
rm -f trust-policy.json task-role-policy.json

echo -e "${GREEN}✅ AWS ECS Infrastructure Setup Complete!${NC}"
