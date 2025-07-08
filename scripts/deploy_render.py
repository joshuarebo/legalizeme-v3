#!/usr/bin/env python3
"""
Render Deployment Script for Kenyan Legal AI
Handles deployment preparation, environment validation, and post-deployment verification
"""

import os
import sys
import json
import subprocess
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RenderDeployment:
    """Handles Render deployment operations"""
    
    def __init__(self):
        self.required_env_vars = [
            'SECRET_KEY',
            'AWS_ACCESS_KEY_ID', 
            'AWS_SECRET_ACCESS_KEY',
            'ANTHROPIC_API_KEY',
            'HUGGING_FACE_TOKEN'
        ]
        
        self.optional_env_vars = [
            'DATABASE_URL',
            'REDIS_URL',
            'ALLOWED_ORIGINS'
        ]
        
        self.deployment_config = {
            'service_name': 'kenyan-legal-ai',
            'health_check_url': '/health',
            'deployment_timeout': 600,  # 10 minutes
            'health_check_retries': 10,
            'health_check_interval': 30
        }
    
    def validate_environment(self) -> Dict[str, Any]:
        """Validate environment variables and configuration"""
        validation_results = {
            'valid': True,
            'missing_required': [],
            'missing_optional': [],
            'warnings': [],
            'errors': []
        }
        
        # Check required environment variables
        for var in self.required_env_vars:
            if not os.getenv(var):
                validation_results['missing_required'].append(var)
                validation_results['valid'] = False
                validation_results['errors'].append(f"Missing required environment variable: {var}")
        
        # Check optional environment variables
        for var in self.optional_env_vars:
            if not os.getenv(var):
                validation_results['missing_optional'].append(var)
                validation_results['warnings'].append(f"Missing optional environment variable: {var}")
        
        # Validate file structure
        required_files = [
            'requirements.txt',
            'app/main.py',
            'app/config.py',
            'render.yaml'
        ]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                validation_results['errors'].append(f"Missing required file: {file_path}")
                validation_results['valid'] = False
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major != 3 or python_version.minor < 11:
            validation_results['warnings'].append(
                f"Python version {python_version.major}.{python_version.minor} detected. "
                "Python 3.11+ recommended for optimal performance."
            )
        
        return validation_results
    
    def prepare_deployment(self) -> Dict[str, Any]:
        """Prepare the application for deployment"""
        logger.info("Preparing deployment...")
        
        preparation_steps = []
        
        try:
            # Generate training data if needed
            if not os.path.exists('data/kenyan_legal_training.jsonl'):
                logger.info("Generating training data...")
                result = subprocess.run([
                    sys.executable, 'scripts/prepare_training_data.py'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    preparation_steps.append("Generated training data successfully")
                else:
                    preparation_steps.append(f"Training data generation failed: {result.stderr}")
            
            # Create necessary directories
            directories = ['data', 'models', 'logs', 'chroma_db', 'reports']
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                preparation_steps.append(f"Created directory: {directory}")
            
            # Validate requirements.txt
            if os.path.exists('requirements.txt'):
                with open('requirements.txt', 'r') as f:
                    requirements = f.read()
                    if 'fastapi' in requirements and 'uvicorn' in requirements:
                        preparation_steps.append("Requirements.txt validated")
                    else:
                        preparation_steps.append("WARNING: Missing core dependencies in requirements.txt")
            
            # Create deployment info file
            deployment_info = {
                'deployment_time': datetime.utcnow().isoformat(),
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'preparation_steps': preparation_steps,
                'environment': os.getenv('ENVIRONMENT', 'production')
            }
            
            with open('deployment_info.json', 'w') as f:
                json.dump(deployment_info, f, indent=2)
            
            preparation_steps.append("Created deployment info file")
            
            return {
                'success': True,
                'steps': preparation_steps,
                'deployment_info': deployment_info
            }
            
        except Exception as e:
            logger.error(f"Deployment preparation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'steps': preparation_steps
            }
    
    async def verify_deployment(self, base_url: str) -> Dict[str, Any]:
        """Verify deployment health and functionality"""
        logger.info(f"Verifying deployment at {base_url}")
        
        verification_results = {
            'health_check': False,
            'api_endpoints': {},
            'response_times': {},
            'errors': []
        }
        
        async with aiohttp.ClientSession() as session:
            # Health check
            try:
                start_time = time.time()
                async with session.get(f"{base_url}/health", timeout=10) as response:
                    response_time = time.time() - start_time
                    verification_results['response_times']['health'] = response_time
                    
                    if response.status == 200:
                        verification_results['health_check'] = True
                        health_data = await response.json()
                        verification_results['health_data'] = health_data
                    else:
                        verification_results['errors'].append(f"Health check failed with status {response.status}")
            
            except Exception as e:
                verification_results['errors'].append(f"Health check error: {str(e)}")
            
            # Test API endpoints
            test_endpoints = [
                '/api/v1/health',
                '/docs',  # Swagger documentation
            ]
            
            for endpoint in test_endpoints:
                try:
                    start_time = time.time()
                    async with session.get(f"{base_url}{endpoint}", timeout=10) as response:
                        response_time = time.time() - start_time
                        verification_results['response_times'][endpoint] = response_time
                        verification_results['api_endpoints'][endpoint] = {
                            'status': response.status,
                            'accessible': response.status < 400
                        }
                
                except Exception as e:
                    verification_results['api_endpoints'][endpoint] = {
                        'status': 'error',
                        'accessible': False,
                        'error': str(e)
                    }
            
            # Test model endpoints (if available)
            model_endpoints = [
                '/models/status',
                '/models/health'
            ]
            
            for endpoint in model_endpoints:
                try:
                    start_time = time.time()
                    async with session.get(f"{base_url}{endpoint}", timeout=15) as response:
                        response_time = time.time() - start_time
                        verification_results['response_times'][endpoint] = response_time
                        verification_results['api_endpoints'][endpoint] = {
                            'status': response.status,
                            'accessible': response.status < 400
                        }
                        
                        if response.status == 200:
                            data = await response.json()
                            verification_results[f'{endpoint}_data'] = data
                
                except Exception as e:
                    verification_results['api_endpoints'][endpoint] = {
                        'status': 'error',
                        'accessible': False,
                        'error': str(e)
                    }
        
        # Calculate overall health score
        total_endpoints = len(verification_results['api_endpoints'])
        accessible_endpoints = sum(
            1 for ep in verification_results['api_endpoints'].values() 
            if ep.get('accessible', False)
        )
        
        verification_results['health_score'] = (
            accessible_endpoints / total_endpoints if total_endpoints > 0 else 0
        )
        
        verification_results['overall_status'] = (
            'healthy' if verification_results['health_check'] and verification_results['health_score'] > 0.7
            else 'degraded' if verification_results['health_score'] > 0.5
            else 'unhealthy'
        )
        
        return verification_results
    
    def generate_deployment_report(
        self, 
        validation: Dict[str, Any],
        preparation: Dict[str, Any],
        verification: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate comprehensive deployment report"""
        
        report_lines = [
            "# Kenyan Legal AI - Deployment Report",
            f"Generated: {datetime.utcnow().isoformat()}",
            "",
            "## Environment Validation",
            f"Status: {'✅ PASSED' if validation['valid'] else '❌ FAILED'}",
            ""
        ]
        
        if validation['errors']:
            report_lines.extend([
                "### Errors:",
                *[f"- {error}" for error in validation['errors']],
                ""
            ])
        
        if validation['warnings']:
            report_lines.extend([
                "### Warnings:",
                *[f"- {warning}" for warning in validation['warnings']],
                ""
            ])
        
        report_lines.extend([
            "## Deployment Preparation",
            f"Status: {'✅ SUCCESS' if preparation['success'] else '❌ FAILED'}",
            "",
            "### Steps Completed:",
            *[f"- {step}" for step in preparation['steps']],
            ""
        ])
        
        if verification:
            report_lines.extend([
                "## Deployment Verification",
                f"Overall Status: {verification['overall_status'].upper()}",
                f"Health Check: {'✅ PASSED' if verification['health_check'] else '❌ FAILED'}",
                f"Health Score: {verification['health_score']:.2%}",
                "",
                "### API Endpoints:",
            ])
            
            for endpoint, data in verification['api_endpoints'].items():
                status_icon = "✅" if data.get('accessible') else "❌"
                report_lines.append(f"- {endpoint}: {status_icon} (Status: {data['status']})")
            
            report_lines.extend([
                "",
                "### Response Times:",
                *[f"- {endpoint}: {time:.3f}s" for endpoint, time in verification['response_times'].items()],
                ""
            ])
            
            if verification['errors']:
                report_lines.extend([
                    "### Verification Errors:",
                    *[f"- {error}" for error in verification['errors']],
                    ""
                ])
        
        report_lines.extend([
            "## Recommendations",
            ""
        ])
        
        if not validation['valid']:
            report_lines.append("- Fix validation errors before deploying")
        
        if validation['missing_optional']:
            report_lines.append("- Consider setting optional environment variables for full functionality")
        
        if verification and verification['health_score'] < 1.0:
            report_lines.append("- Investigate failed endpoints for optimal performance")
        
        report_lines.append("- Monitor application logs after deployment")
        report_lines.append("- Set up alerts for health check failures")
        
        return "\n".join(report_lines)
    
    async def run_full_deployment_check(self, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Run complete deployment validation and verification"""
        logger.info("Starting full deployment check...")
        
        # Step 1: Validate environment
        validation = self.validate_environment()
        logger.info(f"Environment validation: {'PASSED' if validation['valid'] else 'FAILED'}")
        
        # Step 2: Prepare deployment
        preparation = self.prepare_deployment()
        logger.info(f"Deployment preparation: {'SUCCESS' if preparation['success'] else 'FAILED'}")
        
        # Step 3: Verify deployment (if URL provided)
        verification = None
        if base_url:
            verification = await self.verify_deployment(base_url)
            logger.info(f"Deployment verification: {verification['overall_status'].upper()}")
        
        # Step 4: Generate report
        report = self.generate_deployment_report(validation, preparation, verification)
        
        # Save report
        report_filename = f"deployment_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        os.makedirs('reports', exist_ok=True)
        
        with open(f"reports/{report_filename}", 'w') as f:
            f.write(report)
        
        logger.info(f"Deployment report saved: reports/{report_filename}")
        
        return {
            'validation': validation,
            'preparation': preparation,
            'verification': verification,
            'report': report,
            'report_file': f"reports/{report_filename}",
            'overall_success': (
                validation['valid'] and 
                preparation['success'] and 
                (verification is None or verification['overall_status'] in ['healthy', 'degraded'])
            )
        }

async def main():
    """Main deployment check function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kenyan Legal AI Render Deployment")
    parser.add_argument("--validate-only", action="store_true", help="Only validate environment")
    parser.add_argument("--prepare-only", action="store_true", help="Only prepare deployment")
    parser.add_argument("--verify-url", help="URL to verify deployment")
    parser.add_argument("--full-check", action="store_true", help="Run full deployment check")
    
    args = parser.parse_args()
    
    deployment = RenderDeployment()
    
    if args.validate_only:
        validation = deployment.validate_environment()
        print(json.dumps(validation, indent=2))
        sys.exit(0 if validation['valid'] else 1)
    
    elif args.prepare_only:
        preparation = deployment.prepare_deployment()
        print(json.dumps(preparation, indent=2))
        sys.exit(0 if preparation['success'] else 1)
    
    elif args.verify_url:
        verification = await deployment.verify_deployment(args.verify_url)
        print(json.dumps(verification, indent=2))
        sys.exit(0 if verification['overall_status'] in ['healthy', 'degraded'] else 1)
    
    else:
        # Run full check
        result = await deployment.run_full_deployment_check(args.verify_url)
        print(result['report'])
        sys.exit(0 if result['overall_success'] else 1)

if __name__ == "__main__":
    asyncio.run(main())
