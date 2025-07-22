"""
Advanced Security Hardening & Compliance System
Comprehensive security measures, data protection, audit logging, and compliance monitoring.
"""

import asyncio
import logging
import hashlib
import hmac
import secrets
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import re
from functools import wraps
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Security event structure"""
    event_id: str
    event_type: str  # "authentication", "authorization", "data_access", "suspicious_activity"
    severity: str    # "low", "medium", "high", "critical"
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    endpoint: str
    details: Dict[str, Any]
    timestamp: datetime
    resolved: bool

@dataclass
class AuditLogEntry:
    """Audit log entry structure"""
    log_id: str
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: str
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    ip_address: str
    user_agent: str
    timestamp: datetime
    compliance_relevant: bool

@dataclass
class DataProtectionRecord:
    """Data protection record"""
    record_id: str
    data_type: str  # "personal", "legal_document", "ai_model_data"
    classification: str  # "public", "internal", "confidential", "restricted"
    encryption_status: bool
    access_controls: List[str]
    retention_period: int  # days
    created_at: datetime
    last_accessed: datetime
    access_count: int

class SecurityHardening:
    """Advanced security hardening service"""
    
    def __init__(self):
        self.security_events = deque(maxlen=10000)
        self.audit_logs = deque(maxlen=50000)
        self.data_protection_records = {}
        
        # Rate limiting
        self.rate_limits = defaultdict(lambda: deque(maxlen=100))
        
        # Security configuration
        self.security_config = {
            'max_login_attempts': 5,
            'lockout_duration': 900,  # 15 minutes
            'session_timeout': 3600,  # 1 hour
            'password_min_length': 12,
            'require_mfa': True,
            'audit_retention_days': 2555,  # 7 years for legal compliance
            'encryption_key_rotation_days': 90
        }
        
        # Initialize encryption
        self.encryption_key = self._generate_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Initialize database
        self._init_security_database()
        
        # Start security monitoring
        self.monitoring_task = asyncio.create_task(self._security_monitoring_loop())
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key for data protection"""
        try:
            # In production, this would use AWS KMS or similar
            password = secrets.token_bytes(32)
            salt = secrets.token_bytes(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(password))
            return key
            
        except Exception as e:
            logger.error(f"Error generating encryption key: {e}")
            # Fallback to Fernet key generation
            return Fernet.generate_key()
    
    def _init_security_database(self):
        """Initialize security database"""
        try:
            db_path = Path("security_audit.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Security events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT,
                    endpoint TEXT,
                    details TEXT,  -- JSON
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Audit logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    old_values TEXT,  -- JSON
                    new_values TEXT,  -- JSON
                    ip_address TEXT NOT NULL,
                    user_agent TEXT,
                    timestamp TEXT NOT NULL,
                    compliance_relevant BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Data protection records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_protection_records (
                    record_id TEXT PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    encryption_status BOOLEAN DEFAULT TRUE,
                    access_controls TEXT,  -- JSON
                    retention_period INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON security_events(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_severity ON security_events(severity)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)')
            
            conn.commit()
            conn.close()
            
            logger.info("Security database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing security database: {e}")
            raise
    
    async def log_security_event(self, event_type: str, severity: str, 
                                user_id: Optional[str], ip_address: str,
                                user_agent: str, endpoint: str, 
                                details: Dict[str, Any]) -> str:
        """Log security event"""
        try:
            event_id = secrets.token_hex(16)
            
            event = SecurityEvent(
                event_id=event_id,
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                details=details,
                timestamp=datetime.utcnow(),
                resolved=False
            )
            
            # Store in memory
            self.security_events.append(event)
            
            # Store in database
            await self._store_security_event(event)
            
            # Check for critical events
            if severity == "critical":
                await self._handle_critical_security_event(event)
            
            logger.warning(f"Security event [{severity}]: {event_type} from {ip_address}")
            
            return event_id
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
            return ""
    
    async def log_audit_entry(self, user_id: Optional[str], action: str,
                             resource_type: str, resource_id: str,
                             old_values: Optional[Dict[str, Any]],
                             new_values: Optional[Dict[str, Any]],
                             ip_address: str, user_agent: str,
                             compliance_relevant: bool = True) -> str:
        """Log audit entry for compliance"""
        try:
            log_id = secrets.token_hex(16)
            
            audit_entry = AuditLogEntry(
                log_id=log_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow(),
                compliance_relevant=compliance_relevant
            )
            
            # Store in memory
            self.audit_logs.append(audit_entry)
            
            # Store in database
            await self._store_audit_entry(audit_entry)
            
            logger.info(f"Audit log: {action} on {resource_type}:{resource_id} by {user_id}")
            
            return log_id
            
        except Exception as e:
            logger.error(f"Error logging audit entry: {e}")
            return ""
    
    async def encrypt_sensitive_data(self, data: str, data_type: str) -> Tuple[str, str]:
        """Encrypt sensitive data and create protection record"""
        try:
            # Encrypt data
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            encrypted_b64 = base64.b64encode(encrypted_data).decode()
            
            # Create protection record
            record_id = secrets.token_hex(16)
            
            # Determine classification and retention
            classification, retention_days = self._classify_data(data_type)
            
            protection_record = DataProtectionRecord(
                record_id=record_id,
                data_type=data_type,
                classification=classification,
                encryption_status=True,
                access_controls=["authenticated_users"],
                retention_period=retention_days,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                access_count=0
            )
            
            self.data_protection_records[record_id] = protection_record
            await self._store_protection_record(protection_record)
            
            return encrypted_b64, record_id
            
        except Exception as e:
            logger.error(f"Error encrypting sensitive data: {e}")
            raise
    
    async def decrypt_sensitive_data(self, encrypted_data: str, record_id: str,
                                   user_id: Optional[str] = None) -> Optional[str]:
        """Decrypt sensitive data with access logging"""
        try:
            # Check protection record
            if record_id not in self.data_protection_records:
                await self.log_security_event(
                    "data_access", "high", user_id, "unknown", "", "",
                    {"error": "Invalid protection record ID", "record_id": record_id}
                )
                return None
            
            record = self.data_protection_records[record_id]
            
            # Update access tracking
            record.last_accessed = datetime.utcnow()
            record.access_count += 1
            
            # Decrypt data
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes).decode()
            
            # Log access
            await self.log_audit_entry(
                user_id, "decrypt_data", record.data_type, record_id,
                None, None, "system", "system", True
            )
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Error decrypting sensitive data: {e}")
            await self.log_security_event(
                "data_access", "high", user_id, "unknown", "", "",
                {"error": "Decryption failed", "record_id": record_id}
            )
            return None
    
    def _classify_data(self, data_type: str) -> Tuple[str, int]:
        """Classify data and determine retention period"""
        classifications = {
            "personal": ("confidential", 2555),  # 7 years
            "legal_document": ("restricted", 3650),  # 10 years
            "ai_model_data": ("internal", 1825),  # 5 years
            "system_logs": ("internal", 365),  # 1 year
            "audit_logs": ("restricted", 2555),  # 7 years
        }
        
        return classifications.get(data_type, ("internal", 365))
    
    async def check_rate_limit(self, identifier: str, limit: int, 
                              window_seconds: int) -> bool:
        """Check rate limiting"""
        try:
            current_time = time.time()
            requests = self.rate_limits[identifier]
            
            # Remove old requests outside window
            while requests and requests[0] < current_time - window_seconds:
                requests.popleft()
            
            # Check if limit exceeded
            if len(requests) >= limit:
                await self.log_security_event(
                    "rate_limit_exceeded", "medium", None, identifier, "", "",
                    {"limit": limit, "window": window_seconds, "requests": len(requests)}
                )
                return False
            
            # Add current request
            requests.append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error to avoid blocking legitimate requests
    
    async def validate_input_security(self, input_data: str, input_type: str) -> Dict[str, Any]:
        """Validate input for security threats"""
        try:
            validation_result = {
                "is_safe": True,
                "threats_detected": [],
                "sanitized_input": input_data,
                "risk_score": 0.0
            }
            
            # SQL injection detection
            sql_patterns = [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
                r"(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)",
                r"(--|#|/\*|\*/)",
                r"(\b(EXEC|EXECUTE|SP_)\b)"
            ]
            
            for pattern in sql_patterns:
                if re.search(pattern, input_data, re.IGNORECASE):
                    validation_result["threats_detected"].append("sql_injection")
                    validation_result["risk_score"] += 0.3
            
            # XSS detection
            xss_patterns = [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>"
            ]
            
            for pattern in xss_patterns:
                if re.search(pattern, input_data, re.IGNORECASE):
                    validation_result["threats_detected"].append("xss")
                    validation_result["risk_score"] += 0.4
            
            # Command injection detection
            cmd_patterns = [
                r"(\||&|;|\$\(|\`)",
                r"(rm\s+|del\s+|format\s+)",
                r"(wget|curl|nc|netcat)"
            ]
            
            for pattern in cmd_patterns:
                if re.search(pattern, input_data, re.IGNORECASE):
                    validation_result["threats_detected"].append("command_injection")
                    validation_result["risk_score"] += 0.5
            
            # Path traversal detection
            if re.search(r"(\.\./|\.\.\\|%2e%2e)", input_data, re.IGNORECASE):
                validation_result["threats_detected"].append("path_traversal")
                validation_result["risk_score"] += 0.3
            
            # Determine if input is safe
            validation_result["is_safe"] = validation_result["risk_score"] < 0.5
            
            # Sanitize input if needed
            if not validation_result["is_safe"]:
                validation_result["sanitized_input"] = self._sanitize_input(input_data)
            
            # Log security validation
            if validation_result["threats_detected"]:
                await self.log_security_event(
                    "input_validation", "medium", None, "unknown", "", "",
                    {
                        "input_type": input_type,
                        "threats": validation_result["threats_detected"],
                        "risk_score": validation_result["risk_score"]
                    }
                )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating input security: {e}")
            return {
                "is_safe": False,
                "threats_detected": ["validation_error"],
                "sanitized_input": "",
                "risk_score": 1.0
            }
    
    def _sanitize_input(self, input_data: str) -> str:
        """Sanitize potentially dangerous input"""
        # Remove dangerous characters and patterns
        sanitized = re.sub(r"[<>\"'&]", "", input_data)
        sanitized = re.sub(r"(javascript:|data:|vbscript:)", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)\b)", "", sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    async def _store_security_event(self, event: SecurityEvent):
        """Store security event in database"""
        try:
            db_path = Path("security_audit.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_events 
                (event_id, event_type, severity, user_id, ip_address, user_agent, 
                 endpoint, details, timestamp, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id, event.event_type, event.severity, event.user_id,
                event.ip_address, event.user_agent, event.endpoint,
                json.dumps(event.details), event.timestamp.isoformat(), event.resolved
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing security event: {e}")
    
    async def _store_audit_entry(self, audit_entry: AuditLogEntry):
        """Store audit entry in database"""
        try:
            db_path = Path("security_audit.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_logs 
                (log_id, user_id, action, resource_type, resource_id, old_values, 
                 new_values, ip_address, user_agent, timestamp, compliance_relevant)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                audit_entry.log_id, audit_entry.user_id, audit_entry.action,
                audit_entry.resource_type, audit_entry.resource_id,
                json.dumps(audit_entry.old_values) if audit_entry.old_values else None,
                json.dumps(audit_entry.new_values) if audit_entry.new_values else None,
                audit_entry.ip_address, audit_entry.user_agent,
                audit_entry.timestamp.isoformat(), audit_entry.compliance_relevant
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing audit entry: {e}")
    
    async def _store_protection_record(self, record: DataProtectionRecord):
        """Store data protection record in database"""
        try:
            db_path = Path("security_audit.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO data_protection_records 
                (record_id, data_type, classification, encryption_status, access_controls,
                 retention_period, created_at, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.record_id, record.data_type, record.classification,
                record.encryption_status, json.dumps(record.access_controls),
                record.retention_period, record.created_at.isoformat(),
                record.last_accessed.isoformat(), record.access_count
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing protection record: {e}")
    
    async def _handle_critical_security_event(self, event: SecurityEvent):
        """Handle critical security events"""
        try:
            # Log critical event
            logger.critical(f"CRITICAL SECURITY EVENT: {event.event_type} - {event.details}")
            
            # In production, this would:
            # 1. Send alerts to security team
            # 2. Potentially block IP addresses
            # 3. Trigger incident response procedures
            # 4. Notify compliance team
            
        except Exception as e:
            logger.error(f"Error handling critical security event: {e}")
    
    async def _security_monitoring_loop(self):
        """Continuous security monitoring"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Check for suspicious patterns
                await self._detect_suspicious_activity()
                
                # Clean up old records
                await self._cleanup_old_records()
                
            except Exception as e:
                logger.error(f"Error in security monitoring loop: {e}")
    
    async def _detect_suspicious_activity(self):
        """Detect suspicious activity patterns"""
        try:
            # Analyze recent security events for patterns
            recent_events = [e for e in self.security_events 
                           if (datetime.utcnow() - e.timestamp).total_seconds() < 3600]
            
            # Check for multiple failed attempts from same IP
            ip_failures = defaultdict(int)
            for event in recent_events:
                if event.event_type == "authentication" and event.severity in ["medium", "high"]:
                    ip_failures[event.ip_address] += 1
            
            for ip, failures in ip_failures.items():
                if failures >= 5:
                    await self.log_security_event(
                        "suspicious_activity", "high", None, ip, "", "",
                        {"pattern": "multiple_auth_failures", "count": failures}
                    )
            
        except Exception as e:
            logger.error(f"Error detecting suspicious activity: {e}")
    
    async def _cleanup_old_records(self):
        """Clean up old security records based on retention policies"""
        try:
            # This would implement data retention policies
            # For now, just log the cleanup activity
            logger.debug("Security record cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in security cleanup: {e}")

# Global instance
security_compliance = SecurityHardening()
