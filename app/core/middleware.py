"""
FastAPI middleware components
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.logging import app_logger, audit_logger
from app.core.config import settings


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security headers middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details"""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request start
        app_logger.info(
            f"Request started: {request.method} {request.url.path}",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log successful response
            app_logger.info(
                f"Request completed: {request.method} {request.url.path}",
                request_id=request_id,
                status_code=response.status_code,
                process_time=process_time
            )
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            app_logger.error(
                f"Request failed: {request.method} {request.url.path}",
                request_id=request_id,
                error=str(e),
                process_time=process_time
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Internal server error"
                    },
                    "meta": {
                        "request_id": request_id,
                        "timestamp": time.time()
                    }
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting"""
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Simple in-memory rate limiting (use Redis in production)
        current_time = int(time.time() / 60)  # Current minute
        key = f"{client_ip}:{current_time}"
        
        if key not in self.request_counts:
            self.request_counts[key] = 0
        
        self.request_counts[key] += 1
        
        if self.request_counts[key] > self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded"
                    }
                }
            )
        
        # Clean old entries
        current_minute = int(time.time() / 60)
        keys_to_remove = [k for k in self.request_counts.keys() 
                         if int(k.split(':')[1]) < current_minute - 1]
        for key in keys_to_remove:
            del self.request_counts[key]
        
        return await call_next(request)


class CORSMiddleware:
    """CORS middleware configuration"""
    
    @staticmethod
    def get_cors_config():
        """Get CORS configuration"""
        return {
            "allow_origins": settings.ALLOWED_HOSTS,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": [
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-Requested-With",
                "X-Request-ID"
            ]
        }