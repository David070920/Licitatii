"""
Database models based on the schema design
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Decimal, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    login_count = Column(Integer, default=0)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    roles = relationship("UserRole", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    activity = relationship("UserActivity", back_populates="user")
    saved_searches = relationship("SavedSearch", back_populates="user")
    risk_alerts = relationship("RiskAlert", back_populates="user")


class Role(Base):
    """Role model"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    permissions = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    users = relationship("UserRole", back_populates="role")


class UserRole(Base):
    """User role assignment model"""
    __tablename__ = "user_roles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")


class UserProfile(Base):
    """User profile model"""
    __tablename__ = "user_profiles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    company_name = Column(String(255))
    company_cui = Column(String(20))
    company_address = Column(Text)
    phone = Column(String(20))
    subscription_type = Column(String(50), default="free")
    subscription_expires_at = Column(DateTime(timezone=True))
    notification_preferences = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")


class UserSession(Base):
    """User session model"""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class ContractingAuthority(Base):
    """Contracting authority model"""
    __tablename__ = "contracting_authorities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    cui = Column(String(20), unique=True)
    address = Column(Text)
    county = Column(String(50))
    city = Column(String(100))
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    website = Column(String(255))
    authority_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenders = relationship("Tender", back_populates="contracting_authority")


class CPVCode(Base):
    """CPV code model"""
    __tablename__ = "cpv_codes"
    
    code = Column(String(10), primary_key=True)
    description = Column(Text, nullable=False)
    parent_code = Column(String(10))
    level = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenders = relationship("Tender", back_populates="cpv")


class Tender(Base):
    """Tender model"""
    __tablename__ = "tenders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_system = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    contracting_authority_id = Column(Integer, ForeignKey("contracting_authorities.id"))
    cpv_code = Column(String(10), ForeignKey("cpv_codes.code"))
    
    # Tender details
    tender_type = Column(String(50), nullable=False)
    procedure_type = Column(String(50))
    estimated_value = Column(Decimal(15, 2))
    currency = Column(String(3), default="RON")
    
    # Important dates
    publication_date = Column(DateTime(timezone=True))
    submission_deadline = Column(DateTime(timezone=True))
    opening_date = Column(DateTime(timezone=True))
    contract_start_date = Column(DateTime(timezone=True))
    contract_end_date = Column(DateTime(timezone=True))
    
    # Status
    status = Column(String(50), nullable=False)
    
    # Flexible data storage
    raw_data = Column(JSON, default={})
    processed_data = Column(JSON, default={})
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    contracting_authority = relationship("ContractingAuthority", back_populates="tenders")
    cpv = relationship("CPVCode", back_populates="tenders")
    documents = relationship("TenderDocument", back_populates="tender")
    bids = relationship("TenderBid", back_populates="tender")
    awards = relationship("TenderAward", back_populates="tender")
    risk_scores = relationship("TenderRiskScore", back_populates="tender")


class TenderDocument(Base):
    """Tender document model"""
    __tablename__ = "tender_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)
    file_hash = Column(String(64))
    mime_type = Column(String(100))
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    extracted_text = Column(Text)
    metadata = Column(JSON, default={})
    
    # Relationships
    tender = relationship("Tender", back_populates="documents")


class Company(Base):
    """Company model"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    cui = Column(String(20), unique=True)
    registration_number = Column(String(50))
    address = Column(Text)
    county = Column(String(50))
    city = Column(String(100))
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    company_type = Column(String(50))
    company_size = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bids = relationship("TenderBid", back_populates="company")
    awards = relationship("TenderAward", back_populates="company")


class TenderBid(Base):
    """Tender bid model"""
    __tablename__ = "tender_bids"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    # Bid details
    bid_amount = Column(Decimal(15, 2))
    currency = Column(String(3), default="RON")
    bid_date = Column(DateTime(timezone=True))
    
    # Status
    status = Column(String(50), nullable=False)
    is_winner = Column(Boolean, default=False)
    
    # Additional information
    execution_period_days = Column(Integer)
    bid_documents = Column(JSON, default={})
    evaluation_score = Column(Decimal(5, 2))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tender = relationship("Tender", back_populates="bids")
    company = relationship("Company", back_populates="bids")


class TenderAward(Base):
    """Tender award model"""
    __tablename__ = "tender_awards"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    winning_bid_id = Column(UUID(as_uuid=True), ForeignKey("tender_bids.id"))
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    # Award details
    awarded_amount = Column(Decimal(15, 2))
    currency = Column(String(3), default="RON")
    award_date = Column(DateTime(timezone=True))
    contract_number = Column(String(100))
    
    # Contract details
    contract_start_date = Column(DateTime(timezone=True))
    contract_end_date = Column(DateTime(timezone=True))
    contract_value = Column(Decimal(15, 2))
    
    # Status
    status = Column(String(50), nullable=False)
    
    # Additional information
    award_criteria = Column(JSON, default={})
    award_justification = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tender = relationship("Tender", back_populates="awards")
    company = relationship("Company", back_populates="awards")


class RiskAlgorithm(Base):
    """Risk algorithm model"""
    __tablename__ = "risk_algorithms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    algorithm_type = Column(String(50), nullable=False)
    parameters = Column(JSON, default={})
    weight = Column(Decimal(3, 2), default=1.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TenderRiskScore(Base):
    """Tender risk score model"""
    __tablename__ = "tender_risk_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    
    # Risk scores
    overall_risk_score = Column(Decimal(5, 2), nullable=False)
    risk_level = Column(String(20), nullable=False)
    single_bidder_risk = Column(Decimal(5, 2), default=0)
    price_anomaly_risk = Column(Decimal(5, 2), default=0)
    frequency_risk = Column(Decimal(5, 2), default=0)
    geographic_risk = Column(Decimal(5, 2), default=0)
    
    # Analysis details
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    analysis_version = Column(String(20))
    detailed_analysis = Column(JSON, default={})
    
    # Risk flags
    risk_flags = Column(JSON, default=[])
    auto_generated = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tender = relationship("Tender", back_populates="risk_scores")


class RiskAlert(Base):
    """Risk alert model"""
    __tablename__ = "risk_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    risk_score_id = Column(UUID(as_uuid=True), ForeignKey("tender_risk_scores.id"))
    
    # Alert details
    alert_type = Column(String(50), nullable=False)
    alert_level = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    
    # Status
    status = Column(String(20), default="unread")
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True))
    
    # Delivery tracking
    delivery_method = Column(String(20), default="in_app")
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="risk_alerts")


class UserActivity(Base):
    """User activity model"""
    __tablename__ = "user_activity"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Activity details
    action_type = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(255))
    
    # Request details
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_path = Column(String(500))
    request_method = Column(String(10))
    
    # Response details
    response_status = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Metadata
    metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="activity")


class SavedSearch(Base):
    """Saved search model"""
    __tablename__ = "saved_searches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Search details
    search_name = Column(String(255), nullable=False)
    search_query = Column(JSON, nullable=False)
    search_filters = Column(JSON, default={})
    
    # Alert configuration
    alert_enabled = Column(Boolean, default=False)
    alert_frequency = Column(String(20), default="daily")
    last_alert_sent = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="saved_searches")


class DataIngestionLog(Base):
    """Data ingestion log model"""
    __tablename__ = "data_ingestion_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_system = Column(String(50), nullable=False)
    job_id = Column(String(100))
    
    # Job details
    job_type = Column(String(50), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    status = Column(String(20), nullable=False)
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSON, default={})
    
    # Metadata
    metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())