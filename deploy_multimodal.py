#!/usr/bin/env python3
"""
Multi-Modal Legal Document Processing - Production Deployment Script
Automated deployment to AWS ECS with comprehensive validation
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
import boto3
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiModalDeployment:
    """Automated deployment for multi-modal processing system"""
    
    def __init__(self):
        self.aws_region = "us-east-1"
        self.cluster_name = "counsel-cluster"
        self.service_name = "counsel-multimodal-service"
        self.task_family = "counsel-multimodal-task"
        self.ecr_repository = "counsel-multimodal"
        
        # Initialize AWS clients
        self.ecs_client = boto3.client('ecs', region_name=self.aws_region)
        self.ecr_client = boto3.client('ecr', region_name=self.aws_region)
        self.elbv2_client = boto3.client('elbv2', region_name=self.aws_region)
        
        self.deployment_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def validate_prerequisites(self) -> bool:
        """Validate deployment prerequisites"""
        logger.info("🔍 Validating deployment prerequisites...")
        
        checks = []
        
        # Check Docker
        try:
            subprocess.run(['docker', '--version'], check=True, capture_output=True)
            checks.append(("Docker", True, "Available"))
        except (subprocess.CalledProcessError, FileNotFoundError):
            checks.append(("Docker", False, "Not available"))
        
        # Check AWS CLI
        try:
            subprocess.run(['aws', '--version'], check=True, capture_output=True)
            checks.append(("AWS CLI", True, "Available"))
        except (subprocess.CalledProcessError, FileNotFoundError):
            checks.append(("AWS CLI", False, "Not available"))
        
        # Check AWS credentials
        try:
            sts = boto3.client('sts')
            sts.get_caller_identity()
            checks.append(("AWS Credentials", True, "Valid"))
        except Exception as e:
            checks.append(("AWS Credentials", False, f"Invalid: {e}"))
        
        # Check required files
        required_files = [
            "requirements.txt",
            "app/main.py",
            "app/api/routes/multimodal.py",
            "app/services/advanced_multimodal/__init__.py"
        ]
        
        for file_path in required_files:
            if Path(file_path).exists():
                checks.append((f"File: {file_path}", True, "Exists"))
            else:
                checks.append((f"File: {file_path}", False, "Missing"))
        
        # Print validation results
        print("\n📋 Prerequisites Validation:")
        print("=" * 60)
        all_passed = True
        for check_name, passed, message in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}: {message}")
            if not passed:
                all_passed = False
        
        print("=" * 60)
        
        if all_passed:
            logger.info("✅ All prerequisites validated successfully")
        else:
            logger.error("❌ Some prerequisites failed validation")
        
        return all_passed
    
    def build_docker_image(self) -> bool:
        """Build Docker image with multi-modal capabilities"""
        logger.info("🐳 Building Docker image...")
        
        try:
            # Create enhanced Dockerfile
            dockerfile_content = """
FROM python:3.11-slim

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y \\
    tesseract-ocr \\
    tesseract-ocr-eng \\
    libtesseract-dev \\
    poppler-utils \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Set tesseract environment
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/samples logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/multimodal/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
"""
            
            with open("Dockerfile.multimodal", "w") as f:
                f.write(dockerfile_content.strip())
            
            # Build image
            image_tag = f"{self.ecr_repository}:latest"
            build_cmd = [
                "docker", "build",
                "-f", "Dockerfile.multimodal",
                "-t", image_tag,
                "."
            ]
            
            result = subprocess.run(build_cmd, check=True, capture_output=True, text=True)
            logger.info("✅ Docker image built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Docker build failed: {e}")
            logger.error(f"Build output: {e.stdout}")
            logger.error(f"Build errors: {e.stderr}")
            return False
    
    def push_to_ecr(self) -> Optional[str]:
        """Push Docker image to ECR"""
        logger.info("📤 Pushing image to ECR...")
        
        try:
            # Get ECR login token
            auth_response = self.ecr_client.get_authorization_token()
            auth_data = auth_response['authorizationData'][0]
            
            # Extract registry URL
            registry_url = auth_data['proxyEndpoint']
            account_id = registry_url.split('.')[0].split('//')[1]
            
            # Login to ECR
            login_cmd = [
                "aws", "ecr", "get-login-password",
                "--region", self.aws_region
            ]
            login_result = subprocess.run(login_cmd, capture_output=True, text=True, check=True)
            
            docker_login_cmd = [
                "docker", "login",
                "--username", "AWS",
                "--password-stdin",
                registry_url
            ]
            subprocess.run(docker_login_cmd, input=login_result.stdout, text=True, check=True)
            
            # Tag image for ECR
            ecr_image_uri = f"{account_id}.dkr.ecr.{self.aws_region}.amazonaws.com/{self.ecr_repository}:latest"
            tag_cmd = ["docker", "tag", f"{self.ecr_repository}:latest", ecr_image_uri]
            subprocess.run(tag_cmd, check=True)
            
            # Push image
            push_cmd = ["docker", "push", ecr_image_uri]
            subprocess.run(push_cmd, check=True)
            
            logger.info(f"✅ Image pushed to ECR: {ecr_image_uri}")
            return ecr_image_uri
            
        except Exception as e:
            logger.error(f"❌ ECR push failed: {e}")
            return None
    
    def create_task_definition(self, image_uri: str) -> Optional[str]:
        """Create ECS task definition"""
        logger.info("📝 Creating ECS task definition...")
        
        try:
            task_definition = {
                "family": self.task_family,
                "networkMode": "awsvpc",
                "requiresCompatibilities": ["FARGATE"],
                "cpu": "1024",
                "memory": "2048",
                "executionRoleArn": f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/ecsTaskExecutionRole",
                "taskRoleArn": f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/ecsTaskRole",
                "containerDefinitions": [
                    {
                        "name": "counsel-multimodal",
                        "image": image_uri,
                        "portMappings": [
                            {
                                "containerPort": 8000,
                                "protocol": "tcp"
                            }
                        ],
                        "environment": [
                            {"name": "AWS_REGION", "value": self.aws_region},
                            {"name": "ENVIRONMENT", "value": "production"},
                            {"name": "LOG_LEVEL", "value": "INFO"}
                        ],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": "/ecs/counsel-multimodal",
                                "awslogs-region": self.aws_region,
                                "awslogs-stream-prefix": "ecs"
                            }
                        },
                        "healthCheck": {
                            "command": ["CMD-SHELL", "curl -f http://localhost:8000/multimodal/health || exit 1"],
                            "interval": 30,
                            "timeout": 5,
                            "retries": 3,
                            "startPeriod": 60
                        }
                    }
                ]
            }
            
            # Register task definition
            response = self.ecs_client.register_task_definition(**task_definition)
            task_def_arn = response['taskDefinition']['taskDefinitionArn']
            
            logger.info(f"✅ Task definition created: {task_def_arn}")
            return task_def_arn
            
        except Exception as e:
            logger.error(f"❌ Task definition creation failed: {e}")
            return None
    
    def update_service(self, task_definition_arn: str) -> bool:
        """Update ECS service"""
        logger.info("🔄 Updating ECS service...")
        
        try:
            # Check if service exists
            try:
                self.ecs_client.describe_services(
                    cluster=self.cluster_name,
                    services=[self.service_name]
                )
                service_exists = True
            except:
                service_exists = False
            
            if service_exists:
                # Update existing service
                response = self.ecs_client.update_service(
                    cluster=self.cluster_name,
                    service=self.service_name,
                    taskDefinition=task_definition_arn,
                    forceNewDeployment=True
                )
                logger.info("✅ Service updated successfully")
            else:
                logger.warning("⚠️ Service does not exist - manual creation required")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Service update failed: {e}")
            return False
    
    def run_deployment_tests(self) -> bool:
        """Run post-deployment validation tests"""
        logger.info("🧪 Running deployment validation tests...")
        
        try:
            # Import and run test suite
            sys.path.append('.')
            from multimodal_test import MultiModalTestSuite
            
            import asyncio
            
            async def run_tests():
                test_suite = MultiModalTestSuite()
                await test_suite.run_all_tests()
                
                # Check test results
                passed_tests = len([r for r in test_suite.test_results if r["status"] == "PASS"])
                total_tests = len(test_suite.test_results)
                success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
                
                logger.info(f"📊 Test Results: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
                
                return success_rate >= 90  # Require 90% success rate
            
            return asyncio.run(run_tests())
            
        except Exception as e:
            logger.error(f"❌ Deployment tests failed: {e}")
            return False
    
    def deploy(self) -> bool:
        """Execute complete deployment pipeline"""
        logger.info("🚀 Starting Multi-Modal Processing Deployment")
        logger.info(f"📅 Deployment timestamp: {self.deployment_timestamp}")
        
        # Step 1: Validate prerequisites
        if not self.validate_prerequisites():
            logger.error("❌ Prerequisites validation failed")
            return False
        
        # Step 2: Build Docker image
        if not self.build_docker_image():
            logger.error("❌ Docker build failed")
            return False
        
        # Step 3: Push to ECR
        image_uri = self.push_to_ecr()
        if not image_uri:
            logger.error("❌ ECR push failed")
            return False
        
        # Step 4: Create task definition
        task_def_arn = self.create_task_definition(image_uri)
        if not task_def_arn:
            logger.error("❌ Task definition creation failed")
            return False
        
        # Step 5: Update service
        if not self.update_service(task_def_arn):
            logger.error("❌ Service update failed")
            return False
        
        # Step 6: Run validation tests
        if not self.run_deployment_tests():
            logger.error("❌ Deployment validation tests failed")
            return False
        
        logger.info("🎉 Multi-Modal Processing Deployment completed successfully!")
        logger.info("🌐 API endpoints available at: https://api.legalizeme.site/multimodal/")
        
        return True

def main():
    """Main deployment execution"""
    deployment = MultiModalDeployment()
    
    try:
        success = deployment.deploy()
        if success:
            print("\n🎯 DEPLOYMENT SUCCESSFUL! 🎉")
            print("Multi-Modal Legal Document Processing is now live in production.")
            sys.exit(0)
        else:
            print("\n❌ DEPLOYMENT FAILED!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected deployment error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
