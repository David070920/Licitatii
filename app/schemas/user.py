"""
User schemas
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, UUID4
from .base import BaseSchema

class UserBase(BaseSchema):
    """Base user schema"""
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")

class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8, description="User password")

class UserUpdate(BaseSchema):
    """User update schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Last name")
    is_active: Optional[bool] = Field(None, description="User active status")
    is_verified: Optional[bool] = Field(None, description="User verification status")

class UserResponse(BaseSchema):
    """User response schema"""
    id: UUID4 = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    is_active: bool = Field(..., description="User active status")
    is_verified: bool = Field(..., description="User verification status")
    created_at: datetime = Field(..., description="User creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(..., description="Login count")

class UserProfileBase(BaseSchema):
    """Base user profile schema"""
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    company_cui: Optional[str] = Field(None, max_length=20, description="Company CUI")
    company_address: Optional[str] = Field(None, description="Company address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    subscription_type: str = Field(default="free", description="Subscription type")
    notification_preferences: Dict[str, Any] = Field(default_factory=dict, description="Notification preferences")

class UserProfileCreate(UserProfileBase):
    """User profile creation schema"""
    pass

class UserProfileUpdate(BaseSchema):
    """User profile update schema"""
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    company_cui: Optional[str] = Field(None, max_length=20, description="Company CUI")
    company_address: Optional[str] = Field(None, description="Company address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")

class UserProfileResponse(UserProfileBase):
    """User profile response schema"""
    user_id: UUID4 = Field(..., description="User ID")
    subscription_expires_at: Optional[datetime] = Field(None, description="Subscription expiration")
    created_at: datetime = Field(..., description="Profile creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Profile update timestamp")

class UserWithProfile(UserResponse):
    """User with profile schema"""
    profile: Optional[UserProfileResponse] = Field(None, description="User profile")

class UserSettings(BaseSchema):
    """User settings schema"""
    notification_preferences: Dict[str, Any] = Field(default_factory=dict, description="Notification preferences")
    privacy_settings: Dict[str, Any] = Field(default_factory=dict, description="Privacy settings")
    dashboard_preferences: Dict[str, Any] = Field(default_factory=dict, description="Dashboard preferences")

class UserSettingsUpdate(BaseSchema):
    """User settings update schema"""
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")
    privacy_settings: Optional[Dict[str, Any]] = Field(None, description="Privacy settings")
    dashboard_preferences: Optional[Dict[str, Any]] = Field(None, description="Dashboard preferences")

class UserActivity(BaseSchema):
    """User activity schema"""
    id: UUID4 = Field(..., description="Activity ID")
    action_type: str = Field(..., description="Action type")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    created_at: datetime = Field(..., description="Activity timestamp")

class UserActivityResponse(BaseSchema):
    """User activity response schema"""
    activities: List[UserActivity] = Field(..., description="List of activities")
    total: int = Field(..., description="Total activities")

class SavedSearch(BaseSchema):
    """Saved search schema"""
    id: UUID4 = Field(..., description="Search ID")
    search_name: str = Field(..., description="Search name")
    search_query: Dict[str, Any] = Field(..., description="Search query")
    search_filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    alert_enabled: bool = Field(default=False, description="Alert enabled")
    alert_frequency: str = Field(default="daily", description="Alert frequency")
    created_at: datetime = Field(..., description="Search creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Search update timestamp")

class SavedSearchCreate(BaseSchema):
    """Saved search creation schema"""
    search_name: str = Field(..., min_length=1, max_length=255, description="Search name")
    search_query: Dict[str, Any] = Field(..., description="Search query")
    search_filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    alert_enabled: bool = Field(default=False, description="Alert enabled")
    alert_frequency: str = Field(default="daily", regex="^(real_time|daily|weekly)$", description="Alert frequency")

class SavedSearchUpdate(BaseSchema):
    """Saved search update schema"""
    search_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Search name")
    search_query: Optional[Dict[str, Any]] = Field(None, description="Search query")
    search_filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    alert_enabled: Optional[bool] = Field(None, description="Alert enabled")
    alert_frequency: Optional[str] = Field(None, regex="^(real_time|daily|weekly)$", description="Alert frequency")

class UserRole(BaseSchema):
    """User role schema"""
    id: int = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="Role permissions")

class UserRoleAssignment(BaseSchema):
    """User role assignment schema"""
    user_id: UUID4 = Field(..., description="User ID")
    role_id: int = Field(..., description="Role ID")
    assigned_at: datetime = Field(..., description="Assignment timestamp")

class UserSession(BaseSchema):
    """User session schema"""
    id: UUID4 = Field(..., description="Session ID")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    created_at: datetime = Field(..., description="Session creation timestamp")
    expires_at: datetime = Field(..., description="Session expiration timestamp")
    revoked_at: Optional[datetime] = Field(None, description="Session revocation timestamp")

class UserSessionResponse(BaseSchema):
    """User session response schema"""
    sessions: List[UserSession] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total sessions")