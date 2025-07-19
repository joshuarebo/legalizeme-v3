"""
AWS OPENSEARCH DOMAIN MANAGER
============================
Creates and manages AWS OpenSearch domain for production-grade legal document search.
Handles domain creation, configuration, and health monitoring.
"""

import json
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)

class AWSOpenSearchManager:
    """
    AWS OpenSearch domain manager for creating and managing search infrastructure
    """
    
    def __init__(self):
        self.opensearch_client = None
        self.domain_name = "kenyan-legal-search"
        self.domain_endpoint = None
        self._initialized = False
        
        # Domain configuration
        self.domain_config = {
            "DomainName": self.domain_name,
            "ElasticsearchVersion": "OpenSearch_2.3",
            "ClusterConfig": {
                "InstanceType": "t3.small.search",  # Cost-effective for development
                "InstanceCount": 1,
                "DedicatedMasterEnabled": False,
                "ZoneAwarenessEnabled": False
            },
            "EBSOptions": {
                "EBSEnabled": True,
                "VolumeType": "gp3",
                "VolumeSize": 20  # 20GB storage
            },
            "AccessPolicies": json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": f"arn:aws:iam::{self._get_account_id()}:root"
                        },
                        "Action": "es:*",
                        "Resource": f"arn:aws:es:{settings.AWS_REGION}:{self._get_account_id()}:domain/{self.domain_name}/*"
                    }
                ]
            }),
            "EncryptionAtRestOptions": {
                "Enabled": True
            },
            "NodeToNodeEncryptionOptions": {
                "Enabled": True
            },
            "DomainEndpointOptions": {
                "EnforceHTTPS": True,
                "TLSSecurityPolicy": "Policy-Min-TLS-1-2-2019-07"
            },
            "AdvancedSecurityOptions": {
                "Enabled": False  # Simplified for development
            }
        }
    
    def _get_account_id(self) -> str:
        """Get AWS account ID"""
        try:
            sts = boto3.client('sts', 
                             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                             region_name=settings.AWS_REGION)
            return sts.get_caller_identity()['Account']
        except Exception as e:
            logger.warning(f"Could not get account ID: {e}")
            return "123456789012"  # Fallback
    
    async def initialize(self):
        """Initialize OpenSearch manager"""
        if self._initialized:
            return
        
        try:
            # Initialize OpenSearch client
            self.opensearch_client = boto3.client(
                'opensearch',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            # Check if domain exists, create if not
            await self._ensure_domain_exists()
            
            self._initialized = True
            logger.info("AWS OpenSearch Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS OpenSearch Manager: {e}")
            self._initialized = True  # Continue with fallback
    
    async def _ensure_domain_exists(self):
        """Ensure OpenSearch domain exists, create if necessary"""
        try:
            # Check if domain exists
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.opensearch_client.describe_domain(DomainName=self.domain_name)
            )
            
            domain_status = response['DomainStatus']
            self.domain_endpoint = domain_status.get('Endpoint')
            
            if domain_status['Processing']:
                logger.info(f"OpenSearch domain {self.domain_name} is being processed...")
                await self._wait_for_domain_ready()
            else:
                logger.info(f"OpenSearch domain {self.domain_name} is ready at {self.domain_endpoint}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"OpenSearch domain {self.domain_name} not found, creating...")
                await self._create_domain()
            else:
                raise e
    
    async def _create_domain(self):
        """Create new OpenSearch domain"""
        try:
            logger.info(f"Creating OpenSearch domain: {self.domain_name}")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.opensearch_client.create_domain(**self.domain_config)
            )
            
            logger.info(f"OpenSearch domain creation initiated: {response['DomainStatus']['ARN']}")
            
            # Wait for domain to be ready
            await self._wait_for_domain_ready()
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch domain: {e}")
            raise e
    
    async def _wait_for_domain_ready(self, max_wait_minutes: int = 20):
        """Wait for domain to be ready"""
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        logger.info(f"Waiting for OpenSearch domain to be ready (max {max_wait_minutes} minutes)...")
        
        while time.time() - start_time < max_wait_seconds:
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.opensearch_client.describe_domain(DomainName=self.domain_name)
                )
                
                domain_status = response['DomainStatus']
                
                if not domain_status['Processing'] and domain_status.get('Endpoint'):
                    self.domain_endpoint = domain_status['Endpoint']
                    logger.info(f"OpenSearch domain ready at: {self.domain_endpoint}")
                    return True
                
                logger.info(f"Domain still processing... (elapsed: {int(time.time() - start_time)}s)")
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error checking domain status: {e}")
                await asyncio.sleep(30)
        
        logger.warning(f"Domain not ready after {max_wait_minutes} minutes")
        return False
    
    async def get_domain_info(self) -> Dict[str, Any]:
        """Get domain information"""
        try:
            if not self.opensearch_client:
                return {"error": "OpenSearch client not initialized"}
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.opensearch_client.describe_domain(DomainName=self.domain_name)
            )
            
            domain_status = response['DomainStatus']
            
            return {
                "domain_name": domain_status['DomainName'],
                "endpoint": domain_status.get('Endpoint'),
                "processing": domain_status['Processing'],
                "created": domain_status.get('Created', False),
                "deleted": domain_status.get('Deleted', False),
                "elasticsearch_version": domain_status.get('ElasticsearchVersion'),
                "cluster_config": domain_status.get('ClusterConfig', {}),
                "ebs_options": domain_status.get('EBSOptions', {}),
                "encryption_at_rest": domain_status.get('EncryptionAtRestOptions', {}),
                "node_to_node_encryption": domain_status.get('NodeToNodeEncryptionOptions', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting domain info: {e}")
            return {"error": str(e)}
    
    async def delete_domain(self):
        """Delete OpenSearch domain (for cleanup)"""
        try:
            if not self.opensearch_client:
                logger.warning("OpenSearch client not initialized")
                return False
            
            logger.warning(f"Deleting OpenSearch domain: {self.domain_name}")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.opensearch_client.delete_domain(DomainName=self.domain_name)
            )
            
            logger.info(f"Domain deletion initiated: {response['DomainStatus']['ARN']}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting domain: {e}")
            return False
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get connection configuration for OpenSearch client"""
        if not self.domain_endpoint:
            return {}
        
        return {
            "hosts": [{"host": self.domain_endpoint, "port": 443}],
            "http_auth": None,  # Using IAM authentication
            "use_ssl": True,
            "verify_certs": True,
            "ssl_assert_hostname": False,
            "ssl_show_warn": False,
            "connection_class": "RequestsHttpConnection"
        }
    
    async def test_connection(self) -> bool:
        """Test connection to OpenSearch domain"""
        try:
            if not self.domain_endpoint:
                logger.warning("No domain endpoint available")
                return False
            
            # Simple health check
            import requests
            health_url = f"https://{self.domain_endpoint}/_cluster/health"
            
            response = requests.get(health_url, timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"OpenSearch cluster health: {health_data.get('status', 'unknown')}")
                return True
            else:
                logger.warning(f"Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

# Global OpenSearch manager instance
aws_opensearch_manager = AWSOpenSearchManager()
