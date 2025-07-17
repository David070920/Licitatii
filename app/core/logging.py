"""
Logging configuration
"""

import logging
import sys
from typing import Dict, Any
from datetime import datetime
from app.core.config import settings


def setup_logging():
    """Setup application logging"""
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=settings.LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.setFormatter(formatter)
    
    # Create file handler for errors
    file_handler = logging.FileHandler("logs/error.log")
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_logger("app", settings.LOG_LEVEL)
    configure_logger("uvicorn.access", "INFO")
    configure_logger("uvicorn.error", "INFO")
    configure_logger("sqlalchemy.engine", "WARN")


def configure_logger(name: str, level: str):
    """Configure specific logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))


class StructuredLogger:
    """Structured logging utility"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log(self, level: str, message: str, **kwargs):
        """Log structured message"""
        extra_data = {
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra_data)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log("info", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.log("error", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log("warning", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.log("debug", message, **kwargs)


class AuditLogger:
    """Audit logging for security events"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    def log_auth_event(self, event_type: str, user_id: str, ip_address: str, success: bool, **kwargs):
        """Log authentication event"""
        self.logger.info(
            f"AUTH_EVENT: {event_type}",
            extra={
                "event_type": event_type,
                "user_id": user_id,
                "ip_address": ip_address,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )
    
    def log_data_access(self, user_id: str, resource_type: str, resource_id: str, action: str, **kwargs):
        """Log data access event"""
        self.logger.info(
            f"DATA_ACCESS: {action} {resource_type}",
            extra={
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )
    
    def log_system_event(self, event_type: str, message: str, **kwargs):
        """Log system event"""
        self.logger.info(
            f"SYSTEM_EVENT: {event_type}",
            extra={
                "event_type": event_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )


# Global logger instances
app_logger = StructuredLogger("app")
audit_logger = AuditLogger()