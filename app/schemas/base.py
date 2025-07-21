"""
Base Pydantic schemas
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(from_attributes=True)

class PaginationRequest(BaseModel):
    """Pagination request schema"""
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

class PaginationResponse(BaseModel):
    """Pagination response schema"""
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class SortField(BaseModel):
    """Sort field schema"""
    field: str = Field(..., description="Field to sort by")
    order: str = Field(default="asc", regex="^(asc|desc)$", description="Sort order")

class DateRange(BaseModel):
    """Date range schema"""
    from_date: Optional[datetime] = Field(None, alias="from")
    to_date: Optional[datetime] = Field(None, alias="to")

class ValueRange(BaseModel):
    """Value range schema"""
    min_value: Optional[float] = Field(None, alias="min")
    max_value: Optional[float] = Field(None, alias="max")

class APIResponse(BaseModel):
    """Standard API response schema"""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None
    pagination: Optional[PaginationResponse] = None

class ErrorResponse(BaseModel):
    """Error response schema"""
    success: bool = False
    error: Dict[str, Any]
    meta: Dict[str, Any]