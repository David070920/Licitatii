"""
Security utilities for authentication and authorization
"""

import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import User, Role, UserRole
from app.auth.jwt_handler import jwt_handler

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
security = HTTPBearer()

class PasswordManager:
    """Password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_password_reset_token() -> str:
        """Generate secure password reset token"""
        return secrets.token_urlsafe(32)

class AuthService:
    """Authentication service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = self.db.query(User).filter(User.email == email).first()
        
        if not user or not user.is_active:
            return None
        
        if not PasswordManager.verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.login_count += 1
        self.db.commit()
        
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create new user"""
        # Check if user already exists
        if self.get_user_by_email(user_data["email"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Hash password
        hashed_password = PasswordManager.hash_password(user_data["password"])
        
        # Create user
        user = User(
            email=user_data["email"],
            hashed_password=hashed_password,
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            is_active=True,
            is_verified=False
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get user roles"""
        user_roles = self.db.query(UserRole).filter(UserRole.user_id == user_id).all()
        roles = []
        for user_role in user_roles:
            role = self.db.query(Role).filter(Role.id == user_role.role_id).first()
            if role:
                roles.append(role.name)
        return roles
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions from roles"""
        user_roles = self.db.query(UserRole).filter(UserRole.user_id == user_id).all()
        permissions = set()
        
        for user_role in user_roles:
            role = self.db.query(Role).filter(Role.id == user_role.role_id).first()
            if role and role.permissions:
                role_permissions = role.permissions.get("permissions", [])
                permissions.update(role_permissions)
        
        return list(permissions)

class PermissionChecker:
    """Permission checking utilities"""
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthService(db)
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission"""
        user_permissions = self.auth_service.get_user_permissions(user_id)
        return permission in user_permissions or "*" in user_permissions
    
    def has_role(self, user_id: str, role: str) -> bool:
        """Check if user has specific role"""
        user_roles = self.auth_service.get_user_roles(user_id)
        return role in user_roles
    
    def require_permission(self, user_id: str, permission: str):
        """Require specific permission or raise exception"""
        if not self.has_permission(user_id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    
    try:
        payload = jwt_handler.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive"
        )
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        permission_checker = PermissionChecker(db)
        permission_checker.require_permission(str(current_user.id), permission)
        return current_user
    
    return permission_checker

def require_role(role: str):
    """Decorator to require specific role"""
    def role_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        permission_checker = PermissionChecker(db)
        if not permission_checker.has_role(str(current_user.id), role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return current_user
    
    return role_checker