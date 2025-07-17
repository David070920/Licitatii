"""
Test configuration and fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_session
from app.core.config import settings
from app.db.models import User, Role, UserRole, UserProfile
from app.auth.security import PasswordManager

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Create test session factory
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database session override."""
    
    async def override_get_session():
        yield db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    
    # Create citizen role
    citizen_role = Role(
        name="citizen",
        description="Test citizen role",
        permissions=["view_public_tenders", "create_alerts"]
    )
    db_session.add(citizen_role)
    await db_session.commit()
    await db_session.refresh(citizen_role)
    
    # Create user
    user = User(
        email="test@example.com",
        hashed_password=PasswordManager.hash_password("testpassword"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create user profile
    profile = UserProfile(
        user_id=user.id,
        company_name="Test Company",
        subscription_type="free"
    )
    db_session.add(profile)
    
    # Assign role
    user_role = UserRole(
        user_id=user.id,
        role_id=citizen_role.id
    )
    db_session.add(user_role)
    
    await db_session.commit()
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    
    # Create admin role
    admin_role = Role(
        name="admin",
        description="Test admin role",
        permissions=["*"]
    )
    db_session.add(admin_role)
    await db_session.commit()
    await db_session.refresh(admin_role)
    
    # Create admin user
    admin = User(
        email="admin@example.com",
        hashed_password=PasswordManager.hash_password("adminpassword"),
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_verified=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    
    # Create admin profile
    profile = UserProfile(
        user_id=admin.id,
        subscription_type="admin"
    )
    db_session.add(profile)
    
    # Assign role
    user_role = UserRole(
        user_id=admin.id,
        role_id=admin_role.id
    )
    db_session.add(user_role)
    
    await db_session.commit()
    return admin


@pytest.fixture
async def authenticated_client(client: AsyncClient, test_user: User) -> AsyncClient:
    """Create an authenticated test client."""
    
    # Login to get token
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 200
    token_data = response.json()
    
    # Add authorization header
    client.headers["Authorization"] = f"Bearer {token_data['access_token']}"
    
    return client


@pytest.fixture
async def admin_client(client: AsyncClient, admin_user: User) -> AsyncClient:
    """Create an authenticated admin test client."""
    
    # Login to get token
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": admin_user.email,
            "password": "adminpassword"
        }
    )
    
    assert response.status_code == 200
    token_data = response.json()
    
    # Add authorization header
    client.headers["Authorization"] = f"Bearer {token_data['access_token']}"
    
    return client


@pytest.fixture
def sample_tender_data():
    """Sample tender data for testing."""
    return {
        "title": "Software Development Services",
        "description": "Development of web application for public services",
        "source_system": "SICAP",
        "external_id": "TEST001",
        "tender_type": "open",
        "procedure_type": "services",
        "estimated_value": 150000.00,
        "currency": "RON",
        "status": "published"
    }


@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""
    return {
        "name": "Test Company SRL",
        "cui": "RO12345678",
        "address": "Test Address 123",
        "county": "Bucharest",
        "city": "Bucharest",
        "company_type": "SRL",
        "company_size": "medium"
    }


@pytest.fixture
def sample_authority_data():
    """Sample contracting authority data for testing."""
    return {
        "name": "Test Authority",
        "cui": "RO98765432",
        "address": "Authority Address 456",
        "county": "Bucharest",
        "city": "Bucharest",
        "authority_type": "local",
        "contact_email": "contact@testauthority.ro"
    }