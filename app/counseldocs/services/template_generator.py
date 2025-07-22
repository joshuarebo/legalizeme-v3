"""
Template Generator Service for CounselDocs
Generates court documents from Kenya Law Civil Procedure Rules templates.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

import boto3
from botocore.exceptions import ClientError
from jinja2 import Template, Environment, BaseLoader

from app.config import settings

logger = logging.getLogger(__name__)

class TemplateGenerator:
    """
    Generates legal documents from Kenya Law Civil Procedure Rules templates.
    """
    
    def __init__(self):
        """Initialize template generator with AWS services"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # S3 bucket for generated documents
        self.s3_bucket = "counseldocs-documents"
        
        # Load Kenya Law court document templates
        self.court_templates = self._load_court_templates()
    
    def _load_court_templates(self) -> Dict[str, Any]:
        """Load court document templates from Kenya Law Civil Procedure Rules"""
        
        templates = {
            "civil_plaint": {
                "name": "Plaint (Civil Procedure Rules)",
                "category": "civil",
                "description": "Standard plaint for civil cases under Order IV",
                "legal_basis": "Civil Procedure Rules 2010, Order IV, Rule 1",
                "required_fields": [
                    "court_name", "suit_number", "year", "plaintiff_name", 
                    "plaintiff_address", "defendant_name", "defendant_address",
                    "cause_of_action", "relief_sought", "value_of_suit"
                ],
                "optional_fields": [
                    "plaintiff_occupation", "defendant_occupation", "facts",
                    "legal_grounds", "interest_rate", "costs"
                ],
                "template_content": """
IN THE {{ court_name }}
AT {{ court_location }}

CIVIL SUIT NO. {{ suit_number }} OF {{ year }}

BETWEEN

{{ plaintiff_name.upper() }} ................................................ PLAINTIFF
(of {{ plaintiff_address }})

AND

{{ defendant_name.upper() }} ................................................ DEFENDANT
(of {{ defendant_address }})

PLAINT

TO: The above named Defendant

1. The Plaintiff's claim is for:
   {{ relief_sought }}

2. The cause of action arose as follows:
   {{ cause_of_action }}

{% if facts %}
3. PARTICULARS OF THE CLAIM:
   {{ facts }}
{% endif %}

4. The value of the subject matter of this suit is KES {{ value_of_suit }}.

5. This Honourable Court has jurisdiction to hear and determine this matter.

{% if interest_rate %}
6. The Plaintiff claims interest at the rate of {{ interest_rate }}% per annum.
{% endif %}

WHEREFORE the Plaintiff prays for judgment against the Defendant for:
a) {{ relief_sought }}
{% if interest_rate %}
b) Interest at {{ interest_rate }}% per annum from the date of filing this suit to the date of judgment;
{% endif %}
c) Costs of this suit; and
d) Such other relief as this Honourable Court may deem fit to grant.

DATED this _____ day of _____________, {{ year }}.

_________________________
{{ plaintiff_name }}
PLAINTIFF

Filed by:
_________________________
Advocate for the Plaintiff
"""
            },
            
            "affidavit": {
                "name": "Affidavit",
                "category": "civil",
                "description": "Standard affidavit format under Order XIX",
                "legal_basis": "Civil Procedure Rules 2010, Order XIX, Rule 1",
                "required_fields": [
                    "court_name", "suit_number", "year", "deponent_name",
                    "deponent_address", "deponent_occupation", "affidavit_content"
                ],
                "optional_fields": [
                    "exhibits", "commissioner_name", "commissioner_title"
                ],
                "template_content": """
IN THE {{ court_name }}
AT {{ court_location }}

CIVIL SUIT NO. {{ suit_number }} OF {{ year }}

AFFIDAVIT

I, {{ deponent_name.upper() }}, of {{ deponent_address }}, {{ deponent_occupation }}, do solemnly affirm and state as follows:

{{ affidavit_content }}

{% if exhibits %}
The facts deposed to herein are within my knowledge save where otherwise stated and are true to the best of my knowledge and belief.

EXHIBITS:
{{ exhibits }}
{% endif %}

SWORN/AFFIRMED by the said {{ deponent_name }} at _____________ this _____ day of _____________, {{ year }}.

Before me:

_________________________          _________________________
COMMISSIONER FOR OATHS             {{ deponent_name }}
                                   DEPONENT
"""
            }
        }
        
        return templates
    
    async def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available court document templates"""
        
        templates_list = []
        
        for template_id, template_info in self.court_templates.items():
            templates_list.append({
                "template_id": template_id,
                "template_name": template_info["name"],
                "category": template_info["category"],
                "description": template_info["description"],
                "legal_basis": template_info["legal_basis"],
                "required_fields": template_info["required_fields"],
                "optional_fields": template_info.get("optional_fields", [])
            })
        
        return templates_list
    
    async def generate_document(
        self,
        template_id: str,
        template_data: Dict[str, Any],
        user_id: str,
        output_format: str = "pdf",
        custom_filename: Optional[str] = None,
        user_plan: str = "free"
    ) -> Dict[str, Any]:
        """Generate document from template"""
        
        start_time = datetime.utcnow()
        
        try:
            # Validate template
            if template_id not in self.court_templates:
                return {
                    'success': False,
                    'error': f'Template not found: {template_id}',
                    'error_type': 'template_not_found'
                }
            
            template_info = self.court_templates[template_id]
            
            # Validate required fields
            missing_fields = []
            for field in template_info["required_fields"]:
                if field not in template_data or not template_data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    'success': False,
                    'error': f'Missing required fields: {", ".join(missing_fields)}',
                    'error_type': 'missing_fields',
                    'missing_fields': missing_fields
                }
            
            # Generate document content
            template = Template(template_info["template_content"])
            
            # Add default values
            template_data.setdefault('court_location', 'NAIROBI')
            template_data.setdefault('year', datetime.now().year)
            
            # Render template
            rendered_content = template.render(**template_data)
            
            # Generate document based on format
            remove_watermark = user_plan in ["premium", "enterprise", "pro"]

            if output_format.lower() == 'pdf':
                document_result = await self._generate_pdf(rendered_content, template_info, remove_watermark)
            else:
                document_result = await self._generate_html(rendered_content, template_info, remove_watermark)
            
            if not document_result['success']:
                return document_result
            
            # Upload to S3
            generation_id = str(uuid.uuid4())
            filename = custom_filename or f"{template_info['name']}_{generation_id[:8]}"
            
            s3_path = await self._upload_generated_document(
                document_result['content'],
                filename,
                output_format,
                user_id,
                generation_id
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'success': True,
                'generation_id': generation_id,
                'template_id': template_id,
                'template_name': template_info['name'],
                'output_format': output_format,
                'filename': f"{filename}.{output_format}",
                's3_path': s3_path,
                'file_size_bytes': len(document_result['content']),
                'processing_time_seconds': processing_time,
                'generated_at': start_time.isoformat(),
                'download_url': f"/api/v1/counseldocs/generation/download/{generation_id}"
            }
            
        except Exception as e:
            logger.error(f"Document generation failed: {str(e)}")
            return {
                'success': False,
                'error': f"Generation failed: {str(e)}",
                'error_type': 'generation_error'
            }

    async def _generate_pdf(self, content: str, template_info: Dict[str, Any], remove_watermark: bool = False) -> Dict[str, Any]:
        """Generate PDF from HTML content"""

        try:
            # Create professional legal document HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{template_info['name']}</title>
                <style>
                    body {{
                        font-family: 'Times New Roman', serif;
                        font-size: 12pt;
                        line-height: 1.6;
                        color: #000;
                        margin: 2cm;
                        padding: 0;
                    }}
                    .content {{
                        white-space: pre-line;
                        text-align: justify;
                    }}
                    .watermark {{
                        position: fixed;
                        bottom: 10px;
                        right: 10px;
                        font-size: 8pt;
                        color: #666;
                        opacity: 0.7;
                    }}
                </style>
            </head>
            <body>
                <div class="content">{content}</div>
                {'' if remove_watermark else f'''<div class="watermark">
                    Generated by CounselDocs - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
                </div>'''}
            </body>
            </html>
            """

            # For now, return HTML as bytes (WeasyPrint requires additional setup)
            pdf_bytes = html_content.encode('utf-8')

            return {
                'success': True,
                'content': pdf_bytes,
                'content_type': 'text/html'  # Will be PDF in production
            }

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return {
                'success': False,
                'error': f"PDF generation failed: {str(e)}"
            }

    async def _generate_html(self, content: str, template_info: Dict[str, Any], remove_watermark: bool = False) -> Dict[str, Any]:
        """Generate HTML document"""

        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{template_info['name']}</title>
                <style>
                    body {{
                        font-family: 'Times New Roman', serif;
                        font-size: 12pt;
                        line-height: 1.6;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .content {{ white-space: pre-line; text-align: justify; }}
                </style>
            </head>
            <body>
                <div class="content">{content}</div>
            </body>
            </html>
            """

            return {
                'success': True,
                'content': html_content.encode('utf-8'),
                'content_type': 'text/html'
            }

        except Exception as e:
            logger.error(f"HTML generation failed: {e}")
            return {
                'success': False,
                'error': f"HTML generation failed: {str(e)}"
            }

    async def _upload_generated_document(
        self,
        content: bytes,
        filename: str,
        output_format: str,
        user_id: str,
        generation_id: str
    ) -> str:
        """Upload generated document to S3"""

        try:
            s3_key = f"users/{user_id}/generated/{generation_id}_{filename}.{output_format}"

            content_types = {
                'pdf': 'application/pdf',
                'html': 'text/html'
            }

            content_type = content_types.get(output_format, 'application/octet-stream')

            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    'user_id': user_id,
                    'generation_id': generation_id,
                    'filename': filename,
                    'output_format': output_format,
                    'generated_at': datetime.utcnow().isoformat()
                }
            )

            logger.info(f"Generated document uploaded to S3: {s3_key}")
            return s3_key

        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise Exception(f"Failed to upload document: {str(e)}")

    async def get_document_from_s3(self, s3_path: str) -> Optional[bytes]:
        """Retrieve generated document from S3"""

        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_path)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to retrieve document from S3: {e}")
            return None

# Global instance
template_generator = TemplateGenerator()
