"""
Security utilities for authentication
"""

import bcrypt
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_session
from app.db.models import User, UserRole, Role
from app.auth.jwt_handler import jwt_handler
from app.core.logging import audit_logger


security = HTTPBearer()


class PasswordManager:
    """Password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)


class AuthService:
    """Authentication service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        # Get user by email
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Verify password
        if not PasswordManager.verify_password(password, user.hashed_password):
            return None
        
        # Log successful authentication
        audit_logger.log_auth_event(
            "login_success",
            str(user.id),
            "unknown",  # IP will be added by middleware
            True
        )
        
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_roles(self, user_id: str) -> list[str]:
        """Get user roles"""
        result = await self.db.execute(
            select(Role.name)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
        )
        return [role for role in result.scalars()]
    
    async def get_user_permissions(self, user_id: str) -> list[str]:
        """Get user permissions from roles"""
        result = await self.db.execute(
            select(Role.permissions)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
        )
        
        permissions = set()
        for role_permissions in result.scalars():
            if isinstance(role_permissions, list):
                permissions.update(role_permissions)
            elif isinstance(role_permissions, dict):
                permissions.update(role_permissions.get('permissions', []))
        
        return list(permissions)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_session)
) -> User:
    """Get current authenticated user"""
    
    # Verify token
    try:
        payload = jwt_handler.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    # Get user from database
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


class PermissionChecker:
    """Permission checking utilities"""
    
    def __init__(self, required_permission: str):
        self.required_permission = required_permission
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_session)
    ) -> User:
        """Check if user has required permission"""
        
        auth_service = AuthService(db)
        user_permissions = await auth_service.get_user_permissions(str(current_user.id))
        
        # Check for wildcard permission (super admin)
        if "*" in user_permissions:
            return current_user
        
        # Check for specific permission
        if self.required_permission not in user_permissions:
            audit_logger.log_auth_event(
                "permission_denied",
                str(current_user.id),
                "unknown",
                False,
                required_permission=self.required_permission
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user


def require_permission(permission: str):
    """Decorator to require specific permission"""
    return PermissionChecker(permission)


# Common permission dependencies
require_view_tenders = require_permission("view_public_tenders")
require_view_private_tenders = require_permission("view_private_tenders")
require_advanced_search = require_permission("advanced_search")
require_create_alerts = require_permission("create_alerts")
require_api_access = require_permission("api_access")
require_admin_access = require_permission("user_management")
require_system_access = require_permission("system_monitoring")