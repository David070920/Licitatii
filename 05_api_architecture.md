# API Architecture Design for Romanian Public Procurement Platform

## API Design Philosophy

The API follows **RESTful principles** with **OpenAPI 3.0** specification, designed for:
- **Dual Purpose**: Serving both business users and transparency features
- **Performance**: Optimized for high-volume queries and real-time updates
- **Scalability**: Designed to handle growth from 1,000 to 10,000+ users
- **Developer Experience**: Auto-generated documentation, consistent error handling
- **Security**: JWT-based authentication with role-based access control

## API Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                              │
├─────────────────────────────────────────────────────────────────┤
│  Rate Limiting  │  Authentication  │  Load Balancing  │  Logging │
│  (Redis)        │  (JWT)           │  (Nginx)         │  (ELK)   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI APPLICATION                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Business APIs  │  │ Transparency    │  │  Admin APIs     │ │
│  │                 │  │  APIs           │  │                 │ │
│  │  • Tender       │  │  • Public       │  │  • User         │ │
│  │    Search       │  │    Tenders      │  │    Management   │ │
│  │  • Alerts       │  │  • Risk         │  │  • System       │ │
│  │  • Analytics    │  │    Analysis     │  │    Config       │ │
│  │  • Reports      │  │  • Statistics   │  │  • Monitoring   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Core Services  │  │  Shared         │  │  WebSocket      │ │
│  │                 │  │  Components     │  │  APIs           │ │
│  │  • Auth         │  │  • Validation   │  │                 │ │
│  │  • Search       │  │  • Pagination   │  │  • Real-time    │ │
│  │  • Analytics    │  │  • Filtering    │  │    Updates      │ │
│  │  • Risk         │  │  • Caching      │  │  • Notifications│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## API Versioning Strategy

### URL-Based Versioning
```
/api/v1/tenders           # Version 1
/api/v2/tenders           # Version 2 (future)
```

### Version Support Policy
- **Current Version**: v1 (full support)
- **Deprecated Versions**: 12-month support window
- **Breaking Changes**: Major version increment required

## Core API Endpoints

### 1. Authentication & User Management

```yaml
# Authentication endpoints
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
POST   /api/v1/auth/password/reset
POST   /api/v1/auth/password/change
POST   /api/v1/auth/verify-email

# User profile endpoints
GET    /api/v1/users/profile
PUT    /api/v1/users/profile
DELETE /api/v1/users/profile
GET    /api/v1/users/settings
PUT    /api/v1/users/settings
```

### 2. Tender Management APIs

```yaml
# Tender search and retrieval
GET    /api/v1/tenders                    # Search tenders with filters
GET    /api/v1/tenders/{tender_id}        # Get specific tender
GET    /api/v1/tenders/{tender_id}/documents # Get tender documents
GET    /api/v1/tenders/{tender_id}/bids    # Get tender bids
GET    /api/v1/tenders/{tender_id}/history # Get tender history
GET    /api/v1/tenders/{tender_id}/related # Get related tenders

# Advanced search
POST   /api/v1/tenders/search             # Advanced search with complex filters
POST   /api/v1/tenders/bulk-export        # Bulk export tenders
GET    /api/v1/tenders/statistics         # Tender statistics
```

### 3. Business User APIs

```yaml
# Saved searches and alerts
GET    /api/v1/business/saved-searches
POST   /api/v1/business/saved-searches
PUT    /api/v1/business/saved-searches/{search_id}
DELETE /api/v1/business/saved-searches/{search_id}

# Alert management
GET    /api/v1/business/alerts
POST   /api/v1/business/alerts
PUT    /api/v1/business/alerts/{alert_id}
DELETE /api/v1/business/alerts/{alert_id}
POST   /api/v1/business/alerts/{alert_id}/test

# Analytics and reporting
GET    /api/v1/business/analytics/dashboard
GET    /api/v1/business/analytics/trends
GET    /api/v1/business/analytics/competitors
GET    /api/v1/business/reports
POST   /api/v1/business/reports/generate
GET    /api/v1/business/reports/{report_id}
```

### 4. Transparency Platform APIs

```yaml
# Public tender data
GET    /api/v1/transparency/tenders        # Public tender search
GET    /api/v1/transparency/tenders/{tender_id} # Public tender details
GET    /api/v1/transparency/statistics     # Public procurement statistics

# Risk analysis
GET    /api/v1/transparency/risk-analysis  # Risk analysis dashboard
GET    /api/v1/transparency/risk-patterns  # Risk pattern detection
GET    /api/v1/transparency/risk-alerts    # Public risk alerts
GET    /api/v1/transparency/risk-scores/{tender_id} # Tender risk score

# Authority and company analysis
GET    /api/v1/transparency/authorities     # Contracting authorities
GET    /api/v1/transparency/authorities/{authority_id} # Authority profile
GET    /api/v1/transparency/companies       # Company profiles
GET    /api/v1/transparency/companies/{company_id} # Company details
GET    /api/v1/transparency/companies/{company_id}/tenders # Company tender history

# Data visualizations
GET    /api/v1/transparency/visualizations/overview
GET    /api/v1/transparency/visualizations/geographic
GET    /api/v1/transparency/visualizations/temporal
GET    /api/v1/transparency/visualizations/risk-heatmap
```

### 5. Administrative APIs

```yaml
# System administration
GET    /api/v1/admin/system/health
GET    /api/v1/admin/system/metrics
GET    /api/v1/admin/system/logs
POST   /api/v1/admin/system/maintenance

# User management
GET    /api/v1/admin/users
POST   /api/v1/admin/users
PUT    /api/v1/admin/users/{user_id}
DELETE /api/v1/admin/users/{user_id}
POST   /api/v1/admin/users/{user_id}/suspend
POST   /api/v1/admin/users/{user_id}/activate

# Data management
GET    /api/v1/admin/data/sources
POST   /api/v1/admin/data/sources/{source_id}/sync
GET    /api/v1/admin/data/quality
GET    /api/v1/admin/data/ingestion-logs
```

## Request/Response Formats

### 1. Standard Response Format

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789",
    "processing_time_ms": 45
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1250,
    "total_pages": 63
  }
}
```

### 2. Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "TENDER_NOT_FOUND",
    "message": "Tender with ID 'abc123' not found",
    "details": {
      "tender_id": "abc123"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### 3. Validation Error Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "fields": [
        {
          "field": "estimated_value",
          "message": "Value must be greater than 0"
        }
      ]
    }
  }
}
```

## API Request Examples

### 1. Tender Search with Filters

```http
GET /api/v1/tenders?
    status=active&
    cpv_code=45000000&
    estimated_value_min=100000&
    estimated_value_max=1000000&
    contracting_authority=123&
    publication_date_from=2024-01-01&
    page=1&
    per_page=20&
    sort=publication_date&
    order=desc
```

### 2. Advanced Search Request

```http
POST /api/v1/tenders/search
Content-Type: application/json

{
  "filters": {
    "status": ["active", "published"],
    "cpv_codes": ["45000000", "45200000"],
    "estimated_value": {
      "min": 100000,
      "max": 1000000
    },
    "contracting_authorities": [123, 456],
    "publication_date": {
      "from": "2024-01-01",
      "to": "2024-12-31"
    },
    "geographic": {
      "counties": ["Bucharest", "Cluj"],
      "cities": ["Bucharest", "Cluj-Napoca"]
    }
  },
  "search_text": "software development",
  "sort": [
    {"field": "publication_date", "order": "desc"},
    {"field": "estimated_value", "order": "asc"}
  ],
  "pagination": {
    "page": 1,
    "per_page": 20
  }
}
```

### 3. Risk Analysis Request

```http
GET /api/v1/transparency/risk-analysis?
    risk_level=high&
    analysis_date_from=2024-01-01&
    authority_id=123&
    include_patterns=true
```

## API Schemas (Pydantic Models)

### 1. Tender Schema

```python
class TenderResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    contracting_authority: ContractingAuthorityResponse
    cpv_code: str
    cpv_description: str
    tender_type: str
    estimated_value: Optional[Decimal]
    currency: str
    publication_date: datetime
    submission_deadline: Optional[datetime]
    status: str
    risk_score: Optional[RiskScoreResponse]
    created_at: datetime
    updated_at: datetime

class TenderSearchRequest(BaseModel):
    filters: Optional[TenderFilters]
    search_text: Optional[str]
    sort: Optional[List[SortField]]
    pagination: Optional[PaginationRequest]

class TenderFilters(BaseModel):
    status: Optional[List[str]]
    cpv_codes: Optional[List[str]]
    estimated_value: Optional[ValueRange]
    contracting_authorities: Optional[List[int]]
    publication_date: Optional[DateRange]
    geographic: Optional[GeographicFilters]
```

### 2. Risk Analysis Schema

```python
class RiskScoreResponse(BaseModel):
    overall_risk_score: Decimal
    risk_level: str
    single_bidder_risk: Decimal
    price_anomaly_risk: Decimal
    frequency_risk: Decimal
    geographic_risk: Decimal
    analysis_date: datetime
    risk_flags: List[str]

class RiskAnalysisRequest(BaseModel):
    risk_levels: Optional[List[str]]
    analysis_date_range: Optional[DateRange]
    authority_ids: Optional[List[int]]
    include_patterns: bool = False
```

### 3. User Management Schema

```python
class UserRegistrationRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    company_name: Optional[str]
    company_cui: Optional[str]

class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    company_name: Optional[str]
    subscription_type: str
    created_at: datetime
    last_login: Optional[datetime]
```

## API Security

### 1. Authentication Flow

```python
# JWT Token Structure
{
  "sub": "user_id",
  "email": "user@example.com",
  "roles": ["business_user"],
  "permissions": ["read_tenders", "create_alerts"],
  "exp": 1640995200,
  "iat": 1640908800
}

# API Key Structure (for service-to-service)
{
  "key_id": "api_key_123",
  "service": "external_integration",
  "permissions": ["read_public_data"],
  "rate_limit": 1000
}
```

### 2. Rate Limiting

```python
# Rate limiting configuration
RATE_LIMITS = {
    "authenticated": "1000/hour",
    "anonymous": "100/hour",
    "premium": "5000/hour",
    "api_key": "10000/hour"
}

# Rate limit headers
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### 3. Input Validation

```python
# Request validation middleware
class RequestValidator:
    def validate_tender_search(self, request: TenderSearchRequest):
        # Validate search parameters
        # Sanitize input data
        # Check authorization
        pass
        
    def validate_pagination(self, pagination: PaginationRequest):
        # Limit max page size
        # Validate page numbers
        pass
```

## Performance Optimization

### 1. Caching Strategy

```python
# Redis caching configuration
CACHE_KEYS = {
    "tender_search": "search:{hash}",
    "tender_details": "tender:{id}",
    "statistics": "stats:{type}:{period}",
    "risk_analysis": "risk:{tender_id}"
}

CACHE_TTL = {
    "tender_search": 300,  # 5 minutes
    "tender_details": 3600,  # 1 hour
    "statistics": 1800,  # 30 minutes
    "risk_analysis": 7200  # 2 hours
}
```

### 2. Database Query Optimization

```python
# Optimized query examples
class TenderRepository:
    def search_tenders(self, filters: TenderFilters, pagination: Pagination):
        # Use database indexes
        # Implement efficient joins
        # Apply filters in optimal order
        pass
        
    def get_tender_with_relations(self, tender_id: UUID):
        # Use eager loading
        # Optimize N+1 queries
        pass
```

### 3. Response Compression

```python
# Gzip compression for API responses
@app.middleware("http")
async def compress_response(request: Request, call_next):
    response = await call_next(request)
    if "gzip" in request.headers.get("accept-encoding", ""):
        # Compress response body
        pass
    return response
```

## WebSocket API for Real-time Updates

### 1. Connection Management

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
    async def send_tender_update(self, user_id: str, tender_data: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(tender_data)
```

### 2. Real-time Events

```python
# WebSocket event types
class WebSocketEvent:
    TENDER_UPDATED = "tender_updated"
    RISK_ALERT = "risk_alert"
    SEARCH_RESULTS = "search_results"
    SYSTEM_NOTIFICATION = "system_notification"

# Event message format
{
  "type": "tender_updated",
  "data": {
    "tender_id": "abc123",
    "changes": ["status", "estimated_value"]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## API Documentation

### 1. OpenAPI Specification

```yaml
openapi: 3.0.0
info:
  title: Romanian Procurement Platform API
  version: 1.0.0
  description: API for accessing Romanian public procurement data
  contact:
    email: api@procurement-platform.ro
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.procurement-platform.ro/v1
    description: Production server
  - url: https://staging-api.procurement-platform.ro/v1
    description: Staging server

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

### 2. Auto-generated Documentation

```python
# FastAPI automatic documentation
app = FastAPI(
    title="Romanian Procurement Platform API",
    description="API for accessing Romanian public procurement data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Custom documentation themes
app.mount("/docs", get_swagger_ui_html(
    openapi_url="/openapi.json",
    title="API Documentation",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
))
```

## Error Handling

### 1. Error Codes

```python
class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

# Error code definitions
ERROR_CODES = {
    "TENDER_NOT_FOUND": {"message": "Tender not found", "status": 404},
    "UNAUTHORIZED": {"message": "Unauthorized access", "status": 401},
    "RATE_LIMIT_EXCEEDED": {"message": "Rate limit exceeded", "status": 429},
    "VALIDATION_ERROR": {"message": "Request validation failed", "status": 422},
    "INTERNAL_ERROR": {"message": "Internal server error", "status": 500}
}
```

### 2. Error Handler Middleware

```python
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request.headers.get("X-Request-ID")
            }
        }
    )
```

This API architecture provides a comprehensive, scalable, and secure foundation for serving both business users and transparency platform requirements while maintaining high performance and excellent developer experience.