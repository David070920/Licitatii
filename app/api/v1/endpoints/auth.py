"""
Authentication endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from pydantic import BaseModel, EmailStr
from app.core.database import get_session
from app.auth.security import AuthService, PasswordManager
from app.auth.jwt_handler import jwt_handler
from app.db.models import User, UserProfile
from app.core.logging import audit_logger

router = APIRouter()


class UserRegistrationRequest(BaseModel):
    """User registration request model"""
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    company_name: str = None
    company_cui: str = None


class UserLoginResponse(BaseModel):
    """User login response model"""
    access_token: str
    refresh_token: str
    token_type: str
    user_id: str
    email: str


class TokenRefreshRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str


@router.post("/register", response_model=dict)
async def register(
    user_data: UserRegistrationRequest,
    db: AsyncSession = Depends(get_session)
):
    """Register a new user"""
    
    # Check if user already exists
    auth_service = AuthService(db)
    existing_user = await auth_service.get_user_by_email(user_data.email)
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = PasswordManager.hash_password(user_data.password)
    
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        is_verified=False  # Email verification required
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create user profile
    user_profile = UserProfile(
        user_id=new_user.id,
        company_name=user_data.company_name,
        company_cui=user_data.company_cui
    )
    
    db.add(user_profile)
    await db.commit()
    
    # Log registration
    audit_logger.log_auth_event(
        "user_registration",
        str(new_user.id),
        "unknown",
        True,
        email=user_data.email
    )
    
    return {
        "message": "User registered successfully",
        "user_id": str(new_user.id),
        "email": new_user.email
    }


@router.post("/login", response_model=UserLoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session)
):
    """Authenticate user and return JWT tokens"""
    
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        audit_logger.log_auth_event(
            "login_failed",
            "unknown",
            "unknown",
            False,
            email=form_data.username
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Get user roles and permissions
    user_roles = await auth_service.get_user_roles(str(user.id))
    user_permissions = await auth_service.get_user_permissions(str(user.id))
    
    # Create token data
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "roles": user_roles,
        "permissions": user_permissions
    }
    
    # Generate token pair
    tokens = jwt_handler.create_token_pair(token_data)
    
    # Update login statistics
    user.login_count += 1
    user.last_login = func.now()
    await db.commit()
    
    return UserLoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        user_id=str(user.id),
        email=user.email
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_session)
):
    """Refresh access token using refresh token"""
    
    try:
        # Verify refresh token
        payload = jwt_handler.verify_token(refresh_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user and verify they still exist and are active
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Get updated user roles and permissions
        user_roles = await auth_service.get_user_roles(str(user.id))
        user_permissions = await auth_service.get_user_permissions(str(user.id))
        
        # Create new token data
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "roles": user_roles,
            "permissions": user_permissions
        }
        
        # Generate new access token
        new_access_token = jwt_handler.create_access_token(token_data)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)"""
    
    # In a more sophisticated implementation, we would:
    # 1. Add token to blacklist
    # 2. Revoke refresh token
    # 3. Clear session data
    
    return {"message": "Logged out successfully"}


@router.post("/password-reset")
async def password_reset(
    email: EmailStr,
    db: AsyncSession = Depends(get_session)
):
    """Request password reset"""
    
    # In a real implementation, this would:
    # 1. Generate reset token
    # 2. Send email with reset link
    # 3. Store token with expiration
    
    return {"message": "Password reset instructions sent to email"}


@router.post("/verify-email")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_session)
):
    """Verify email address"""
    
    # In a real implementation, this would:
    # 1. Verify email verification token
    # 2. Mark user as verified
    # 3. Enable account
    
    return {"message": "Email verified successfully"}