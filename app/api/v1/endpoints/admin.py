"""
Admin endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime
from app.core.database import get_session
from app.auth.security import require_permission
from app.db.models import User, UserProfile, DataIngestionLog, UserActivity
from app.core.logging import app_logger

router = APIRouter()


class UserResponse(BaseModel):
    """User response model"""
    id: UUID4
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    login_count: int

    class Config:
        from_attributes = True


class SystemHealthResponse(BaseModel):
    """System health response model"""
    status: str
    timestamp: datetime
    database: dict
    services: dict
    metrics: dict


class SystemMetricsResponse(BaseModel):
    """System metrics response model"""
    users: dict
    tenders: dict
    api_usage: dict
    data_ingestion: dict
    performance: dict


class DataIngestionLogResponse(BaseModel):
    """Data ingestion log response model"""
    id: UUID4
    source_system: str
    job_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    records_processed: int
    records_created: int
    records_updated: int
    records_failed: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


@router.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health(
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_permission("system_monitoring"))
):
    """Get system health status"""
    
    # Check database connectivity
    try:
        await db.execute(select(func.now()))
        db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy"
    
    # Mock service health checks
    services = {
        "database": {"status": db_status, "response_time": "15ms"},
        "redis": {"status": "healthy", "response_time": "5ms"},
        "celery": {"status": "healthy", "workers": 4},
        "elasticsearch": {"status": "healthy", "response_time": "25ms"}
    }
    
    # Mock metrics
    metrics = {
        "memory_usage": 68.5,
        "cpu_usage": 42.3,
        "disk_usage": 55.2,
        "active_connections": 15,
        "requests_per_minute": 124
    }
    
    overall_status = "healthy" if all(s["status"] == "healthy" for s in services.values()) else "degraded"
    
    return SystemHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        database={"status": db_status, "connections": 15},
        services=services,
        metrics=metrics
    )


@router.get("/system/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_permission("system_monitoring"))
):
    """Get system metrics"""
    
    # Get user metrics
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()
    
    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_users_result.scalar()
    
    # Mock other metrics
    metrics = SystemMetricsResponse(
        users={
            "total": total_users,
            "active": active_users,
            "new_this_month": 45,
            "login_rate": 78.5
        },
        tenders={
            "total": 1250,
            "active": 89,
            "processed_today": 23,
            "average_processing_time": "2.5 minutes"
        },
        api_usage={
            "requests_today": 15420,
            "requests_per_minute": 124,
            "average_response_time": "125ms",
            "error_rate": 0.8
        },
        data_ingestion={
            "jobs_today": 8,
            "successful_jobs": 7,
            "failed_jobs": 1,
            "last_sync": "2024-01-15T14:30:00Z"
        },
        performance={
            "memory_usage": 68.5,
            "cpu_usage": 42.3,
            "disk_usage": 55.2,
            "uptime": "7 days, 14 hours"
        }
    )
    
    return metrics


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_permission("user_management"))
):
    """Get users list"""
    
    stmt = select(User)
    
    if search:
        stmt = stmt.where(
            User.email.ilike(f"%{search}%") |
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%")
        )
    
    if active_only:
        stmt = stmt.where(User.is_active == True)
    
    stmt = stmt.order_by(User.created_at.desc())
    
    # Apply pagination
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return [UserResponse.from_orm(user) for user in users]


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: UUID4,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_permission("user_management"))
):
    """Activate user account"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    await db.commit()
    
    app_logger.info(
        "User activated by admin",
        admin_id=str(current_user.id),
        user_id=str(user_id)
    )
    
    return {"message": "User activated successfully"}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID4,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_permission("user_management"))
):
    """Deactivate user account"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    await db.commit()
    
    app_logger.info(
        "User deactivated by admin",
        admin_id=str(current_user.id),
        user_id=str(user_id)
    )
    
    return {"message": "User deactivated successfully"}


@router.get("/data/ingestion-logs", response_model=List[DataIngestionLogResponse])
async def get_ingestion_logs(
    source_system: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_permission("data_management"))
):
    """Get data ingestion logs"""
    
    stmt = select(DataIngestionLog)
    
    if source_system:
        stmt = stmt.where(DataIngestionLog.source_system == source_system)
    
    if status:
        stmt = stmt.where(DataIngestionLog.status == status)
    
    stmt = stmt.order_by(DataIngestionLog.created_at.desc()).limit(limit)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    return [DataIngestionLogResponse.from_orm(log) for log in logs]


@router.post("/data/sync/{source_system}")
async def trigger_data_sync(
    source_system: str,
    current_user = Depends(require_permission("data_management"))
):
    """Trigger data synchronization for a source system"""
    
    # This would typically queue a background job
    # For now, return a mock response
    
    app_logger.info(
        "Data sync triggered by admin",
        admin_id=str(current_user.id),
        source_system=source_system
    )
    
    return {
        "message": f"Data sync triggered for {source_system}",
        "job_id": "sync_job_123456",
        "status": "queued"
    }


@router.get("/data/quality")
async def get_data_quality(
    current_user = Depends(require_permission("data_management"))
):
    """Get data quality metrics"""
    
    # Mock data quality metrics
    return {
        "overall_score": 87.5,
        "completeness": 92.3,
        "accuracy": 89.1,
        "consistency": 85.7,
        "timeliness": 91.2,
        "issues": [
            {
                "type": "missing_data",
                "description": "Some tenders missing estimated values",
                "count": 23,
                "severity": "medium"
            },
            {
                "type": "duplicate_data",
                "description": "Potential duplicate tenders detected",
                "count": 5,
                "severity": "low"
            }
        ],
        "recommendations": [
            "Implement additional validation for estimated values",
            "Add duplicate detection algorithm",
            "Review data ingestion process for SICAP"
        ]
    }


@router.get("/logs")
async def get_system_logs(
    level: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    current_user = Depends(require_permission("system_monitoring"))
):
    """Get system logs"""
    
    # This would typically read from log files or logging system
    # For now, return mock data
    
    return {
        "logs": [
            {
                "timestamp": "2024-01-15T14:30:00Z",
                "level": "INFO",
                "message": "User login successful",
                "user_id": "user_123",
                "ip_address": "192.168.1.100"
            },
            {
                "timestamp": "2024-01-15T14:25:00Z",
                "level": "ERROR",
                "message": "Database connection failed",
                "error": "Connection timeout",
                "retry_count": 3
            },
            {
                "timestamp": "2024-01-15T14:20:00Z",
                "level": "INFO",
                "message": "Data ingestion completed",
                "source": "SICAP",
                "records_processed": 156
            }
        ],
        "total": 1250,
        "page": 1,
        "has_more": True
    }


@router.get("/activity")
async def get_user_activity(
    user_id: Optional[UUID4] = Query(None),
    action_type: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_permission("user_management"))
):
    """Get user activity logs"""
    
    stmt = select(UserActivity)
    
    if user_id:
        stmt = stmt.where(UserActivity.user_id == user_id)
    
    if action_type:
        stmt = stmt.where(UserActivity.action_type == action_type)
    
    stmt = stmt.order_by(UserActivity.created_at.desc()).limit(limit)
    
    result = await db.execute(stmt)
    activities = result.scalars().all()
    
    return [
        {
            "id": str(activity.id),
            "user_id": str(activity.user_id),
            "action_type": activity.action_type,
            "resource_type": activity.resource_type,
            "resource_id": activity.resource_id,
            "ip_address": activity.ip_address,
            "created_at": activity.created_at.isoformat(),
            "metadata": activity.metadata
        }
        for activity in activities
    ]


@router.post("/maintenance")
async def start_maintenance_mode(
    maintenance_message: str = "System maintenance in progress",
    current_user = Depends(require_permission("system_monitoring"))
):
    """Start maintenance mode"""
    
    # This would typically set a maintenance flag in Redis or database
    # For now, return a mock response
    
    app_logger.info(
        "Maintenance mode started",
        admin_id=str(current_user.id),
        message=maintenance_message
    )
    
    return {
        "message": "Maintenance mode activated",
        "maintenance_message": maintenance_message,
        "started_at": datetime.utcnow().isoformat()
    }


@router.delete("/maintenance")
async def stop_maintenance_mode(
    current_user = Depends(require_permission("system_monitoring"))
):
    """Stop maintenance mode"""
    
    app_logger.info(
        "Maintenance mode stopped",
        admin_id=str(current_user.id)
    )
    
    return {
        "message": "Maintenance mode deactivated",
        "stopped_at": datetime.utcnow().isoformat()
    }