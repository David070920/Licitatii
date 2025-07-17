"""
Authentication endpoint tests
"""

import pytest
from httpx import AsyncClient
from app.db.models import User


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    
    user_data = {
        "email": "newuser@example.com",
        "password": "testpassword123",
        "first_name": "New",
        "last_name": "User",
        "company_name": "Test Company"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert "user_id" in data
    assert data["message"] == "User registered successfully"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    """Test registration with duplicate email."""
    
    user_data = {
        "email": test_user.email,
        "password": "testpassword123",
        "first_name": "Duplicate",
        "last_name": "User"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_login_valid_credentials(client: AsyncClient, test_user: User):
    """Test login with valid credentials."""
    
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == str(test_user.id)
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user: User):
    """Test login with invalid credentials."""
    
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent user."""
    
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user: User):
    """Test token refresh."""
    
    # First login to get tokens
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword"
        }
    )
    
    assert login_response.status_code == 200
    login_data = login_response.json()
    
    # Use refresh token to get new access token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]}
    )
    
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert "access_token" in refresh_data
    assert refresh_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    """Test refresh with invalid token."""
    
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Could not refresh token"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """Test logout endpoint."""
    
    response = await client.post("/api/v1/auth/logout")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_password_reset_request(client: AsyncClient, test_user: User):
    """Test password reset request."""
    
    response = await client.post(
        "/api/v1/auth/password-reset",
        params={"email": test_user.email}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password reset instructions sent to email"


@pytest.mark.asyncio
async def test_email_verification(client: AsyncClient):
    """Test email verification endpoint."""
    
    response = await client.post(
        "/api/v1/auth/verify-email",
        params={"token": "mock_verification_token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Email verified successfully"


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test accessing protected endpoint without token."""
    
    response = await client.get("/api/v1/business/dashboard")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_token(authenticated_client: AsyncClient):
    """Test accessing protected endpoint with valid token."""
    
    response = await authenticated_client.get("/api/v1/business/dashboard")
    
    assert response.status_code == 200
    data = response.json()
    assert "total_tenders_monitored" in data
    assert "active_alerts" in data