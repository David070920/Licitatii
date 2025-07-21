"""
Authentication endpoints
"""

from datetime import datetime, timedelta
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Depends, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.security import AuthService, PasswordManager, get_current_user, get_current_active_user
from app.auth.jwt_handler import jwt_handler
from app.schemas.auth import (
    UserRegistrationRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
    EmailVerificationRequest,
    AuthenticationResponse,
    UserPermissions
)
from app.schemas.user import UserResponse, UserProfileCreate
from app.db.models import User, UserProfile, Role, UserRole
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    auth_service = AuthService(db)
    
    try:
        # Create user
        user = auth_service.create_user({
            "email": user_data.email,
            "password": user_data.password,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name
        })
        
        # Create user profile if company data provided
        if user_data.company_name or user_data.company_cui:
            profile = UserProfile(
                user_id=user.id,
                company_name=user_data.company_name,
                company_cui=user_data.company_cui,
                subscription_type="free"
            )
            db.add(profile)
        
        # Assign default role (citizen)
        default_role = db.query(Role).filter(Role.name == "citizen").first()
        if not default_role:
            # Create default role if it doesn't exist
            default_role = Role(
                name="citizen",
                description="Registered Citizen",
                permissions={
                    "permissions": [
                        "view_public_tenders",
                        "view_public_statistics",
                        "view_risk_transparency",
                        "create_alerts",
                        "save_searches",
                        "comment_tenders"
                    ]
                }
            )
            db.add(default_role)
            db.commit()
            db.refresh(default_role)
        
        user_role = UserRole(user_id=user.id, role_id=default_role.id)
        db.add(user_role)
        db.commit()
        
        return user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """User login"""
    auth_service = AuthService(db)
    
    # Authenticate user
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user permissions
    user_permissions = auth_service.get_user_permissions(str(user.id))
    user_roles = auth_service.get_user_roles(str(user.id))
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt_handler.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "roles": user_roles,
            "permissions": user_permissions
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = jwt_handler.create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    try:
        # Decode refresh token
        payload = jwt_handler.decode_token(token_data.refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not user_id or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user and permissions
        auth_service = AuthService(db)
        user = auth_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        user_permissions = auth_service.get_user_permissions(user_id)
        user_roles = auth_service.get_user_roles(user_id)
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = jwt_handler.create_access_token(
            data={
                "sub": user_id,
                "email": user.email,
                "roles": user_roles,
                "permissions": user_permissions
            },
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": token_data.refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """User logout"""
    # In a real implementation, you would invalidate the token
    # For now, we'll just return a success message
    return {"message": "Successfully logged out"}

@router.post("/password/reset")
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset"""
    auth_service = AuthService(db)
    user = auth_service.get_user_by_email(request.email)
    
    if not user:
        # Don't reveal if user exists or not
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = PasswordManager.generate_password_reset_token()
    
    # In a real implementation, you would:
    # 1. Store the reset token in the database with expiration
    # 2. Send email with reset link
    
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/password/reset/confirm")
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset"""
    # In a real implementation, you would:
    # 1. Validate the reset token
    # 2. Update the user's password
    # 3. Invalidate the reset token
    
    return {"message": "Password has been reset successfully"}

@router.post("/password/change")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not PasswordManager.verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = PasswordManager.hash_password(request.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}

@router.post("/verify-email")
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify user email"""
    # In a real implementation, you would:
    # 1. Validate the verification token
    # 2. Mark user as verified
    
    return {"message": "Email verified successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user

@router.get("/me/permissions", response_model=UserPermissions)
async def get_current_user_permissions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user permissions"""
    auth_service = AuthService(db)
    user_permissions = auth_service.get_user_permissions(str(current_user.id))
    user_roles = auth_service.get_user_roles(str(current_user.id))
    
    return UserPermissions(
        permissions=user_permissions,
        roles=user_roles
    )