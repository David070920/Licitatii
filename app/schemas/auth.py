"""
Authentication schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from .base import BaseSchema

class UserRegistrationRequest(BaseSchema):
    """User registration request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    company_cui: Optional[str] = Field(None, max_length=20, description="Company CUI")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLoginRequest(BaseSchema):
    """User login request schema"""
    username: str = Field(..., description="Username (email)")
    password: str = Field(..., description="User password")

class TokenResponse(BaseSchema):
    """Token response schema"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema"""
    refresh_token: str = Field(..., description="Refresh token")

class PasswordResetRequest(BaseSchema):
    """Password reset request schema"""
    email: EmailStr = Field(..., description="User email address")

class PasswordResetConfirm(BaseSchema):
    """Password reset confirmation schema"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class PasswordChangeRequest(BaseSchema):
    """Password change request schema"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class EmailVerificationRequest(BaseSchema):
    """Email verification request schema"""
    token: str = Field(..., description="Email verification token")

class MFASetupRequest(BaseSchema):
    """MFA setup request schema"""
    method: str = Field(..., regex="^(totp|sms|email)$", description="MFA method")

class MFAVerifyRequest(BaseSchema):
    """MFA verification request schema"""
    code: str = Field(..., min_length=6, max_length=6, description="MFA code")

class UserPermissions(BaseSchema):
    """User permissions schema"""
    permissions: List[str] = Field(..., description="List of user permissions")
    roles: List[str] = Field(..., description="List of user roles")

class AuthenticationResponse(BaseSchema):
    """Authentication response schema"""
    user: "UserResponse"
    tokens: TokenResponse
    permissions: UserPermissions

# Import at the end to avoid circular imports
from .user import UserResponse
AuthenticationResponse.model_rebuild()