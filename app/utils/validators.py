import re
import logging
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urlparse
from pathlib import Path
import mimetypes

logger = logging.getLogger(__name__)

def validate_query(query: str, max_length: int = 2000) -> Dict[str, Any]:
    """Validate a legal query input"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    if not query:
        result['valid'] = False
        result['errors'].append('Query cannot be empty')
        return result
    
    if not isinstance(query, str):
        result['valid'] = False
        result['errors'].append('Query must be a string')
        return result
    
    # Check length
    if len(query) > max_length:
        result['valid'] = False
        result['errors'].append(f'Query exceeds maximum length of {max_length} characters')
    
    # Check for minimum length
    if len(query.strip()) < 10:
        result['valid'] = False
        result['errors'].append('Query is too short (minimum 10 characters)')
    
    # Check for potentially malicious content
    malicious_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<form[^>]*>',
        r'<input[^>]*>',
        r'eval\s*\(',
        r'document\.cookie',
        r'window\.location'
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            result['valid'] = False
            result['errors'].append('Query contains potentially malicious content')
            break
    
    # Check for SQL injection patterns
    sql_patterns = [
        r'(?:\'|\"|\`|\-\-|\*|\/\*|\*\/)',
        r'(?:union|select|insert|update|delete|drop|create|alter|exec|execute)\s',
        r'(?:or|and)\s+(?:1=1|\'1\'=\'1\'|\"1\"=\"1\")',
        r'(?:;|\||\|\|)',
        r'(?:<|>|=|!|%|_)'
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            result['warnings'].append('Query contains SQL-like syntax')
            break
    
    # Check for reasonable word count
    word_count = len(query.split())
    if word_count > 500:
        result['warnings'].append('Query is very long and may not produce optimal results')
    elif word_count < 3:
        result['warnings'].append('Query is very short and may not provide enough context')
    
    return result

def validate_document_type(document_type: str) -> Dict[str, Any]:
    """Validate document type for generation"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    valid_types = [
        'contract',
        'agreement',
        'notice',
        'petition',
        'affidavit',
        'memorandum',
        'lease',
        'will',
        'power_of_attorney',
        'employment_contract',
        'service_agreement',
        'non_disclosure_agreement',
        'partnership_agreement',
        'sale_agreement',
        'rental_agreement',
        'loan_agreement',
        'license_agreement',
        'franchise_agreement',
        'joint_venture_agreement',
        'shareholder_agreement'
    ]
    
    if not document_type:
        result['valid'] = False
        result['errors'].append('Document type cannot be empty')
        return result
    
    if not isinstance(document_type, str):
        result['valid'] = False
        result['errors'].append('Document type must be a string')
        return result
    
    # Normalize document type
    normalized_type = document_type.lower().strip().replace(' ', '_')
    
    if normalized_type not in valid_types:
        result['valid'] = False
        result['errors'].append(f'Invalid document type. Must be one of: {", ".join(valid_types)}')
    
    return result

def validate_email(email: str) -> Dict[str, Any]:
    """Validate email address"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    if not email:
        result['valid'] = False
        result['errors'].append('Email cannot be empty')
        return result
    
    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        result['valid'] = False
        result['errors'].append('Invalid email format')
    
    # Check length
    if len(email) > 254:
        result['valid'] = False
        result['errors'].append('Email is too long')
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'\.{2,}',  # Multiple consecutive dots
        r'^\.|\.$',  # Starting or ending with dot
        r'@.*@',  # Multiple @ symbols
        r'[<>]',  # Angle brackets
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, email):
            result['valid'] = False
            result['errors'].append('Email contains invalid characters')
            break
    
    return result

def validate_password(password: str) -> Dict[str, Any]:
    """Validate password strength"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'strength': 'weak'
    }
    
    if not password:
        result['valid'] = False
        result['errors'].append('Password cannot be empty')
        return result
    
    # Check minimum length
    if len(password) < 8:
        result['valid'] = False
        result['errors'].append('Password must be at least 8 characters long')
    
    # Check maximum length
    if len(password) > 128:
        result['valid'] = False
        result['errors'].append('Password is too long (maximum 128 characters)')
    
    # Check for character types
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:,.<>?]', password))
    
    strength_score = sum([has_upper, has_lower, has_digit, has_special])
    
    if strength_score < 3:
        result['valid'] = False
        result['errors'].append('Password must contain at least 3 of: uppercase, lowercase, digit, special character')
    
    # Determine strength
    if strength_score == 4 and len(password) >= 12:
        result['strength'] = 'very_strong'
    elif strength_score == 4 and len(password) >= 10:
        result['strength'] = 'strong'
    elif strength_score >= 3 and len(password) >= 8:
        result['strength'] = 'medium'
    else:
        result['strength'] = 'weak'
    
    # Check for common patterns
    common_patterns = [
        r'123456',
        r'password',
        r'qwerty',
        r'abc123',
        r'admin',
        r'welcome',
        r'login',
        r'user',
        r'test'
    ]
    
    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            result['warnings'].append('Password contains common patterns')
            break
    
    return result

def validate_url(url: str) -> Dict[str, Any]:
    """Validate URL format"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    if not url:
        result['valid'] = False
        result['errors'].append('URL cannot be empty')
        return result
    
    try:
        parsed = urlparse(url)
        
        if not parsed.scheme:
            result['valid'] = False
            result['errors'].append('URL must include a scheme (http/https)')
        
        if not parsed.netloc:
            result['valid'] = False
            result['errors'].append('URL must include a domain')
        
        # Check for valid schemes
        valid_schemes = ['http', 'https', 'ftp', 'ftps']
        if parsed.scheme not in valid_schemes:
            result['valid'] = False
            result['errors'].append(f'Invalid URL scheme. Must be one of: {", ".join(valid_schemes)}')
        
        # Check length
        if len(url) > 2048:
            result['valid'] = False
            result['errors'].append('URL is too long')
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'javascript:',
            r'vbscript:',
            r'data:',
            r'<script',
            r'<iframe',
            r'<object',
            r'<embed'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                result['valid'] = False
                result['errors'].append('URL contains potentially malicious content')
                break
        
    except Exception as e:
        result['valid'] = False
        result['errors'].append(f'Invalid URL format: {str(e)}')
    
    return result

def validate_file_upload(filename: str, file_size: int, max_size_mb: int = 10) -> Dict[str, Any]:
    """Validate file upload"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    if not filename:
        result['valid'] = False
        result['errors'].append('Filename cannot be empty')
        return result
    
    # Check file extension
    allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf']
    file_extension = Path(filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        result['valid'] = False
        result['errors'].append(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}')
    
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        result['valid'] = False
        result['errors'].append(f'File size exceeds maximum of {max_size_mb}MB')
    
    # Check filename for suspicious patterns
    suspicious_patterns = [
        r'\.{2,}',  # Multiple dots
        r'[<>:"/\\|?*]',  # Invalid filename characters
        r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)',  # Windows reserved names
        r'^\.',  # Starting with dot
        r'\.$',  # Ending with dot
        r'^\s|\s$'  # Leading/trailing spaces
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, filename, re.IGNORECASE):
            result['valid'] = False
            result['errors'].append('Filename contains invalid characters')
            break
    
    # Check filename length
    if len(filename) > 255:
        result['valid'] = False
        result['errors'].append('Filename is too long')
    
    return result

def validate_phone_number(phone: str, country_code: str = '+254') -> Dict[str, Any]:
    """Validate phone number (Kenya specific)"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    if not phone:
        result['valid'] = False
        result['errors'].append('Phone number cannot be empty')
        return result
    
    # Remove spaces and dashes
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Kenya phone number patterns
    kenyan_patterns = [
        r'^\+254[17]\d{8}$',  # +254 7XX XXX XXX or +254 1XX XXX XXX
        r'^0[17]\d{8}$',  # 07XX XXX XXX or 01XX XXX XXX
        r'^\+254\d{9}$',  # General +254 format
        r'^0\d{9}$'  # General 0 format
    ]
    
    is_valid = any(re.match(pattern, clean_phone) for pattern in kenyan_patterns)
    
    if not is_valid:
        result['valid'] = False
        result['errors'].append('Invalid phone number format for Kenya')
    
    return result

def validate_json_data(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Validate JSON data against a simple schema"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    def validate_field(value: Any, field_schema: Dict[str, Any], field_name: str):
        field_type = field_schema.get('type')
        required = field_schema.get('required', False)
        
        if value is None:
            if required:
                result['errors'].append(f'Field "{field_name}" is required')
                result['valid'] = False
            return
        
        # Type validation
        if field_type == 'string' and not isinstance(value, str):
            result['errors'].append(f'Field "{field_name}" must be a string')
            result['valid'] = False
        elif field_type == 'integer' and not isinstance(value, int):
            result['errors'].append(f'Field "{field_name}" must be an integer')
            result['valid'] = False
        elif field_type == 'number' and not isinstance(value, (int, float)):
            result['errors'].append(f'Field "{field_name}" must be a number')
            result['valid'] = False
        elif field_type == 'boolean' and not isinstance(value, bool):
            result['errors'].append(f'Field "{field_name}" must be a boolean')
            result['valid'] = False
        elif field_type == 'array' and not isinstance(value, list):
            result['errors'].append(f'Field "{field_name}" must be an array')
            result['valid'] = False
        elif field_type == 'object' and not isinstance(value, dict):
            result['errors'].append(f'Field "{field_name}" must be an object')
            result['valid'] = False
        
        # Length validation for strings
        if field_type == 'string' and isinstance(value, str):
            min_length = field_schema.get('min_length')
            max_length = field_schema.get('max_length')
            
            if min_length and len(value) < min_length:
                result['errors'].append(f'Field "{field_name}" must be at least {min_length} characters')
                result['valid'] = False
            
            if max_length and len(value) > max_length:
                result['errors'].append(f'Field "{field_name}" must not exceed {max_length} characters')
                result['valid'] = False
        
        # Range validation for numbers
        if field_type in ['integer', 'number'] and isinstance(value, (int, float)):
            min_value = field_schema.get('min_value')
            max_value = field_schema.get('max_value')
            
            if min_value is not None and value < min_value:
                result['errors'].append(f'Field "{field_name}" must be at least {min_value}')
                result['valid'] = False
            
            if max_value is not None and value > max_value:
                result['errors'].append(f'Field "{field_name}" must not exceed {max_value}')
                result['valid'] = False
    
    try:
        if not isinstance(data, dict):
            result['valid'] = False
            result['errors'].append('Data must be a JSON object')
            return result
        
        # Validate each field in schema
        for field_name, field_schema in schema.items():
            field_value = data.get(field_name)
            validate_field(field_value, field_schema, field_name)
        
        # Check for extra fields
        extra_fields = set(data.keys()) - set(schema.keys())
        if extra_fields:
            result['warnings'].append(f'Extra fields found: {", ".join(extra_fields)}')
        
    except Exception as e:
        result['valid'] = False
        result['errors'].append(f'Validation error: {str(e)}')
    
    return result

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and other attacks"""
    if not isinstance(text, str):
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remove JavaScript
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove event handlers
    text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    # Remove dangerous protocols
    text = re.sub(r'(javascript|vbscript|data|file):', '', text, flags=re.IGNORECASE)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def validate_kenyan_id_number(id_number: str) -> Dict[str, Any]:
    """Validate Kenyan ID number"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    if not id_number:
        result['valid'] = False
        result['errors'].append('ID number cannot be empty')
        return result
    
    # Remove spaces and dashes
    clean_id = re.sub(r'[\s\-]', '', id_number)
    
    # Check if it's all digits
    if not clean_id.isdigit():
        result['valid'] = False
        result['errors'].append('ID number must contain only digits')
        return result
    
    # Check length (Kenyan ID should be 7-8 digits)
    if len(clean_id) < 7 or len(clean_id) > 8:
        result['valid'] = False
        result['errors'].append('Kenyan ID number must be 7-8 digits long')
    
    return result
