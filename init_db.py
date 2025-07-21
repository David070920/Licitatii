#!/usr/bin/env python3
"""
Database initialization script
"""

import os
import sys
from sqlalchemy.orm import Session
from app.core.database import engine, SessionLocal, create_tables
from app.db.models import Role, User, UserRole, UserProfile, ContractingAuthority, CPVCode
from app.auth.security import PasswordManager

def create_default_roles(db: Session):
    """Create default roles if they don't exist"""
    roles_data = [
        {
            "name": "anonymous",
            "description": "Anonymous User",
            "permissions": {
                "permissions": [
                    "view_public_tenders",
                    "view_public_statistics",
                    "view_risk_transparency"
                ]
            }
        },
        {
            "name": "citizen",
            "description": "Registered Citizen",
            "permissions": {
                "permissions": [
                    "view_public_tenders",
                    "view_public_statistics",
                    "view_risk_transparency",
                    "create_alerts",
                    "save_searches",
                    "comment_tenders"
                ]
            }
        },
        {
            "name": "business_basic",
            "description": "Business User - Basic",
            "permissions": {
                "permissions": [
                    "view_public_tenders",
                    "view_private_tenders",
                    "advanced_search",
                    "create_alerts",
                    "save_searches",
                    "basic_analytics",
                    "export_data_limited"
                ]
            }
        },
        {
            "name": "business_premium",
            "description": "Business User - Premium",
            "permissions": {
                "permissions": [
                    "view_public_tenders",
                    "view_private_tenders",
                    "advanced_search",
                    "create_alerts",
                    "save_searches",
                    "full_analytics",
                    "export_data_unlimited",
                    "api_access",
                    "competitor_analysis",
                    "custom_reports"
                ]
            }
        },
        {
            "name": "admin",
            "description": "Administrator",
            "permissions": {
                "permissions": [
                    "user_management",
                    "content_moderation",
                    "system_monitoring",
                    "data_management",
                    "report_generation"
                ]
            }
        },
        {
            "name": "super_admin",
            "description": "Super Administrator",
            "permissions": {
                "permissions": ["*"]
            }
        }
    ]
    
    for role_data in roles_data:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(**role_data)
            db.add(role)
            print(f"Created role: {role_data['name']}")
    
    db.commit()

def create_admin_user(db: Session):
    """Create default admin user if it doesn't exist"""
    admin_email = "admin@licitatii.ro"
    existing_user = db.query(User).filter(User.email == admin_email).first()
    
    if not existing_user:
        admin_user = User(
            email=admin_email,
            hashed_password=PasswordManager.hash_password("admin123"),
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_verified=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # Create profile
        profile = UserProfile(
            user_id=admin_user.id,
            company_name="Romanian Procurement Platform",
            subscription_type="admin"
        )
        db.add(profile)
        
        # Assign super_admin role
        super_admin_role = db.query(Role).filter(Role.name == "super_admin").first()
        if super_admin_role:
            user_role = UserRole(user_id=admin_user.id, role_id=super_admin_role.id)
            db.add(user_role)
        
        db.commit()
        print(f"Created admin user: {admin_email}")
        print("Admin password: admin123")

def create_sample_authorities(db: Session):
    """Create sample contracting authorities"""
    authorities_data = [
        {
            "name": "Primaria Municipiului Bucuresti",
            "cui": "4267833",
            "county": "Bucuresti",
            "city": "Bucuresti",
            "authority_type": "local",
            "contact_email": "contact@pmb.ro"
        },
        {
            "name": "Consiliul Judetean Cluj",
            "cui": "4540067",
            "county": "Cluj",
            "city": "Cluj-Napoca",
            "authority_type": "local",
            "contact_email": "contact@cjcluj.ro"
        },
        {
            "name": "Ministerul Sanatatii",
            "cui": "4267166",
            "county": "Bucuresti",
            "city": "Bucuresti",
            "authority_type": "central",
            "contact_email": "contact@ms.ro"
        }
    ]
    
    for auth_data in authorities_data:
        existing_auth = db.query(ContractingAuthority).filter(
            ContractingAuthority.cui == auth_data["cui"]
        ).first()
        
        if not existing_auth:
            authority = ContractingAuthority(**auth_data)
            db.add(authority)
            print(f"Created authority: {auth_data['name']}")
    
    db.commit()

def create_sample_cpv_codes(db: Session):
    """Create sample CPV codes"""
    cpv_codes_data = [
        {"code": "45000000", "description": "Construction work", "level": 1},
        {"code": "45200000", "description": "Work for complete or part construction and civil engineering work", "level": 2},
        {"code": "72000000", "description": "IT services: consulting, software development, Internet and support", "level": 1},
        {"code": "72200000", "description": "Software programming and consultancy services", "level": 2},
        {"code": "79000000", "description": "Business services: law, marketing, consulting, recruitment, printing and security", "level": 1},
        {"code": "79600000", "description": "Services related to the printing industry", "level": 2},
    ]
    
    for cpv_data in cpv_codes_data:
        existing_cpv = db.query(CPVCode).filter(CPVCode.code == cpv_data["code"]).first()
        
        if not existing_cpv:
            cpv_code = CPVCode(**cpv_data)
            db.add(cpv_code)
            print(f"Created CPV code: {cpv_data['code']} - {cpv_data['description']}")
    
    db.commit()

def init_database():
    """Initialize database with default data"""
    print("Initializing database...")
    
    # Create tables
    print("Creating database tables...")
    create_tables()
    
    # Create session
    db = SessionLocal()
    
    try:
        # Create default roles
        print("Creating default roles...")
        create_default_roles(db)
        
        # Create admin user
        print("Creating admin user...")
        create_admin_user(db)
        
        # Create sample authorities
        print("Creating sample authorities...")
        create_sample_authorities(db)
        
        # Create sample CPV codes
        print("Creating sample CPV codes...")
        create_sample_cpv_codes(db)
        
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()