# Comprehensive Architecture Overview - Romanian Public Procurement Platform

## Executive Summary

This document provides a complete architectural overview of the Romanian Public Procurement Platform, designed as a superior alternative to e-licitatie.ro. The platform serves dual purposes: advanced procurement monitoring for businesses and radical transparency for citizens and journalists.

## Project Requirements Summary

### Core Objectives
- **Business Service**: Advanced tender monitoring and analytics for companies
- **Transparency Platform**: Public access to procurement data with risk analysis
- **Scale**: Initial 1,000 business users, 10,000 citizens, designed for 10x growth
- **Budget**: Startup approach with cost-effective, open-source solutions
- **Timeline**: 3-6 months for MVP, with clear scaling path

### Data Sources
- **SICAP (SEAP)**: Primary Romanian procurement system
- **ANRMAP**: National regulatory authority data
- **Local Municipalities**: Various municipal websites
- **EU TED**: European tender database

### Risk Detection Focus
- Single bidder tenders
- Unusual pricing patterns
- Frequent winner patterns
- Geographic clustering anomalies

## Architecture Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND LAYER                                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│   Business Dashboard        │    Citizen Portal         │    Admin Panel              │
│   (React/Vue.js)           │    (React/Vue.js)         │    (React/Vue.js)           │
│                            │                           │                             │
│   • Advanced Search        │    • Public Tenders       │    • User Management        │
│   • Analytics Dashboard    │    • Risk Analysis        │    • System Monitoring      │
│   • Alerts & Reports       │    • Transparency Tools    │    • Data Management        │
│   • API Access            │    • Visualizations       │    • Configuration          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            │ HTTPS/WebSocket
                                            │
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                 API GATEWAY                                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│   Rate Limiting (Redis)  │  Authentication (JWT)  │  Load Balancing  │  Logging (ELK)  │
│   • 1000 req/hour        │  • Role-based access   │  • Nginx         │  • Request logs  │
│   • User tier limits     │  • MFA support         │  • Health checks │  • Audit trail  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            │ Internal API
                                            │
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           CORE APPLICATION (FastAPI)                                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│ │ Authentication  │ │ Tender Service  │ │ Risk Detection  │ │ Analytics Service       │ │
│ │ Service         │ │ Module          │ │ Module          │ │ Module                  │ │
│ │                 │ │                 │ │                 │ │                         │ │
│ │ • JWT tokens    │ │ • CRUD ops      │ │ • Single bidder │ │ • Aggregations          │ │
│ │ • Role-based    │ │ • Search/filter │ │ • Price anomaly │ │ • Trend analysis        │ │
│ │   access        │ │ • Documents     │ │ • Freq winners  │ │ • Dashboard data        │ │
│ │ • Sessions      │ │ • Lifecycle     │ │ • Geo clustering│ │ • Custom reports        │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────────────┘ │
│                                                                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│ │ Notification    │ │ Reporting       │ │ User Management │ │ Data Ingestion          │ │
│ │ Module          │ │ Module          │ │ Module          │ │ Controller              │ │
│ │                 │ │                 │ │                 │ │                         │ │
│ │ • Email alerts  │ │ • PDF reports   │ │ • Profiles      │ │ • Orchestration         │ │
│ │ • In-app notifs │ │ • Excel export  │ │ • Subscriptions │ │ • Job scheduling        │ │
│ │ • WebSocket     │ │ • Custom queries│ │ • Preferences   │ │ • Error handling        │ │
│ │ • Templates     │ │ • Visualizations│ │ • Activity logs │ │ • Quality monitoring    │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────────────┘ │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            │ Background Tasks
                                            │
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          BACKGROUND PROCESSING (Celery)                                  │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│ │ Data Ingestion  │ │ Risk Analysis   │ │ Report          │ │ Notification            │ │
│ │ Workers         │ │ Workers         │ │ Generation      │ │ Delivery                │ │
│ │                 │ │                 │ │                 │ │                         │ │
│ │ • SICAP scraper │ │ • Algorithm     │ │ • PDF creation  │ │ • Email sending         │ │
│ │ • ANRMAP sync   │ │   execution     │ │ • Excel export  │ │ • SMS alerts            │ │
│ │ • EU TED import │ │ • Pattern       │ │ • Scheduled     │ │ • Push notifications    │ │
│ │ • Municipality  │ │   detection     │ │   reports       │ │ • Digest emails         │ │
│ │   scraping      │ │ • Score calc    │ │ • Custom        │ │ • Bulk messaging        │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────────────┘ │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            │ Data Storage
                                            │
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DATA LAYER                                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│ │ PostgreSQL 15+  │ │ Redis Cache     │ │ File Storage    │ │ Monitoring Data         │ │
│ │ (Primary DB)    │ │ (In-memory)     │ │ (Documents)     │ │ (Metrics)               │ │
│ │                 │ │                 │ │                 │ │                         │ │
│ │ • Tenders       │ │ • Sessions      │ │ • PDFs          │ │ • Performance           │ │
│ │ • Companies     │ │ • API cache     │ │ • Images        │ │ • Business metrics      │ │
│ │ • Users         │ │ • Rate limits   │ │ • Reports       │ │ • System health         │ │
│ │ • Risk scores   │ │ • Temp data     │ │ • Backups       │ │ • Error tracking        │ │
│ │ • Analytics     │ │ • Queue data    │ │ • Logs          │ │ • Usage analytics       │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────────────┘ │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            │ External Data
                                            │
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL DATA SOURCES                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│ │ SICAP (SEAP)    │ │ ANRMAP          │ │ Local Munic.    │ │ EU TED Database         │ │
│ │                 │ │                 │ │ Websites        │ │                         │ │
│ │ • Web scraping  │ │ • API + scraping│ │ • Web scraping  │ │ • Official APIs         │ │
│ │ • Real-time     │ │ • Daily sync    │ │ • Weekly sync   │ │ • XML feeds             │ │
│ │ • Primary source│ │ • Regulatory    │ │ • Diverse       │ │ • Romanian subset       │ │
│ │ • 1-5K tenders  │ │ • 500-1K tender │ │ • 200-500       │ │ • 100-300 tenders       │ │
│ │   daily         │ │   daily         │ │   tenders/day   │ │   daily                 │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────────────┘ │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack Summary

### Core Framework: **FastAPI**
**Selected for**: High performance, async support, rapid development, excellent API documentation

### Database Stack
- **PostgreSQL 15+**: Primary database with JSONB support and full-text search
- **Redis**: Caching, sessions, rate limiting, task queues
- **File Storage**: Local/cloud storage for documents and reports

### Development & Deployment
- **Python 3.11+**: Core language with modern features
- **Docker**: Containerization for consistent deployment
- **Celery**: Background task processing
- **Nginx**: Reverse proxy and load balancing
- **GitHub Actions**: CI/CD pipeline

### Infrastructure (Cost-Optimized)
- **Phase 1**: Single server deployment ($100-200/month)
- **Phase 2**: Load-balanced multi-server ($300-500/month)
- **Phase 3**: Microservices architecture ($1000-2000/month)

## Key Architectural Decisions

### 1. Modular Monolith Approach
- **Rationale**: Rapid MVP development while maintaining clear service boundaries
- **Benefits**: Easy debugging, simple deployment, shared resources
- **Future**: Clear path to microservices extraction

### 2. FastAPI Framework Selection
- **Performance**: Async/await support for concurrent operations
- **Developer Experience**: Auto-generated OpenAPI documentation
- **Startup Friendly**: Minimal boilerplate, rapid prototyping
- **Scalability**: Designed for high-performance API applications

### 3. PostgreSQL as Primary Database
- **JSONB Support**: Flexible schema for diverse tender data formats
- **Full-text Search**: Built-in search capabilities
- **ACID Compliance**: Critical for financial data integrity
- **Scalability**: Read replicas and horizontal scaling support

### 4. Risk Detection Algorithm Design
- **Weighted Scoring**: Composite risk scores from multiple algorithms
- **Statistical Analysis**: Uses z-scores, isolation forests for anomaly detection
- **Pattern Recognition**: Detects systematic irregularities
- **Configurable Thresholds**: Adaptable to different risk tolerance levels

## Data Flow Architecture

### 1. Data Ingestion Flow
```
External Sources → Scrapers → Validation → Transformation → 
Enrichment → Duplicate Detection → Database Storage → 
Risk Analysis → Alert Generation → User Notifications
```

### 2. User Request Flow
```
Frontend → API Gateway → Authentication → Rate Limiting → 
Core Service → Database Query → Data Processing → 
Response Formatting → Caching → Frontend
```

### 3. Risk Analysis Flow
```
New Tender → Background Worker → Risk Algorithms → 
Score Calculation → Pattern Detection → Alert Generation → 
Notification Delivery → Dashboard Updates
```

## Security Architecture

### Authentication & Authorization
- **JWT Tokens**: Stateless authentication with refresh tokens
- **Role-Based Access Control**: Granular permissions for different user types
- **Multi-Factor Authentication**: TOTP, SMS, email verification
- **API Key Management**: For programmatic access with rate limiting

### Data Protection
- **Encryption**: TLS 1.3 for transit, AES-256 for rest
- **Input Validation**: Comprehensive sanitization and validation
- **Audit Logging**: Complete activity tracking
- **Privacy Compliance**: GDPR-compliant data handling

### Security Headers & Middleware
- **CORS Configuration**: Strict cross-origin policies
- **Rate Limiting**: Per-user and per-endpoint limits
- **Security Headers**: CSP, HSTS, XSS protection
- **Circuit Breakers**: Fault tolerance and resilience

## Performance Optimization Strategy

### Database Optimization
- **Indexing Strategy**: Optimized indexes for frequent queries
- **Query Optimization**: Efficient joins and filtering
- **Connection Pooling**: Managed database connections
- **Read Replicas**: Separate read/write workloads

### Caching Architecture
- **Application Cache**: Redis for frequently accessed data
- **API Response Cache**: Cached query results
- **CDN Integration**: Static asset delivery
- **Database Query Cache**: Expensive query result caching

### Asynchronous Processing
- **Background Tasks**: Celery for heavy computations
- **Event-Driven Updates**: Real-time data processing
- **Batch Processing**: Efficient bulk operations
- **Queue Management**: Task prioritization and throttling

## Scalability Design

### Phase 1: Modular Monolith (MVP)
- **Users**: 1,000 business, 10,000 citizens
- **Infrastructure**: Single server with Docker
- **Database**: PostgreSQL with Redis cache
- **Cost**: $100-200/month

### Phase 2: Service Extraction (Growth)
- **Users**: 10,000 business, 100,000 citizens
- **Infrastructure**: Multiple app servers with load balancer
- **Database**: Primary with read replicas
- **Cost**: $300-500/month

### Phase 3: Microservices (Scale)
- **Users**: 50,000+ business, 500,000+ citizens
- **Infrastructure**: Kubernetes cluster
- **Database**: Distributed with sharding
- **Cost**: $1,000-2,000/month

## Risk Detection Capabilities

### Algorithm Suite
1. **Single Bidder Detection**: Identifies monopolistic patterns
2. **Price Anomaly Detection**: Statistical outlier identification
3. **Frequent Winner Analysis**: Pattern recognition for repeated winners
4. **Geographic Clustering**: Spatial analysis of procurement patterns

### Risk Scoring
- **Composite Scores**: Weighted combination of algorithm results
- **Risk Levels**: Low, Medium, High, Critical classifications
- **Alert System**: Automated notifications for high-risk tenders
- **Pattern Analysis**: Cross-tender pattern detection

## API Design

### RESTful Architecture
- **Standard HTTP Methods**: GET, POST, PUT, DELETE
- **Resource-Based URLs**: Intuitive endpoint structure
- **Consistent Response Format**: Standardized JSON responses
- **Error Handling**: Comprehensive error codes and messages

### API Endpoints (Key Examples)
```
# Authentication
POST /api/v1/auth/login
POST /api/v1/auth/register

# Tender Management
GET /api/v1/tenders
GET /api/v1/tenders/{id}
POST /api/v1/tenders/search

# Business Features
GET /api/v1/business/analytics/dashboard
GET /api/v1/business/alerts
POST /api/v1/business/saved-searches

# Transparency Features
GET /api/v1/transparency/risk-analysis
GET /api/v1/transparency/statistics
GET /api/v1/transparency/companies/{id}
```

## Deployment Strategy

### MVP Deployment (Single Server)
```yaml
Architecture:
  - Nginx (reverse proxy)
  - FastAPI application (Gunicorn)
  - PostgreSQL database
  - Redis cache
  - Celery workers
  - Basic monitoring
```

### Scaled Deployment (Multi-Server)
```yaml
Architecture:
  - Load balancer (Nginx)
  - Multiple app servers
  - Database cluster
  - Redis cluster
  - Dedicated worker nodes
  - Monitoring stack
```

## Monitoring & Observability

### Application Monitoring
- **Health Checks**: Service availability
- **Performance Metrics**: Response times, throughput
- **Error Tracking**: Exception monitoring
- **Resource Usage**: CPU, memory, disk monitoring

### Business Metrics
- **User Activity**: Registration, engagement patterns
- **Data Quality**: Ingestion success rates
- **Risk Detection**: Algorithm performance
- **System Performance**: Query optimization needs

## Data Management

### Data Ingestion Pipeline
- **Scheduled Jobs**: Regular data synchronization
- **Real-time Processing**: Immediate tender updates
- **Quality Assurance**: Validation and error handling
- **Duplicate Detection**: Intelligent deduplication

### Data Storage Strategy
- **Partitioning**: Time-based data organization
- **Archiving**: Historical data management
- **Backup Strategy**: Regular encrypted backups
- **Data Retention**: Compliance with regulations

## Quality Assurance

### Code Quality
- **Type Hints**: Full Python type annotations
- **Testing**: Unit, integration, and end-to-end tests
- **Code Review**: Peer review process
- **Static Analysis**: Automated code quality checks

### Data Quality
- **Validation Rules**: Input data validation
- **Consistency Checks**: Cross-source data validation
- **Completeness Monitoring**: Missing data detection
- **Accuracy Metrics**: Data quality dashboards

## Cost Optimization

### Infrastructure Efficiency
- **Resource Scaling**: Auto-scaling based on demand
- **Spot Instances**: Cost-effective compute resources
- **Storage Optimization**: Compressed historical data
- **Network Optimization**: CDN and data transfer optimization

### Development Efficiency
- **Open Source**: Maximum use of free tools
- **Automation**: Reduced manual operations
- **Monitoring**: Proactive issue detection
- **Documentation**: Reduced onboarding time

## Compliance & Legal

### Data Privacy
- **GDPR Compliance**: European data protection regulations
- **Data Anonymization**: Personal data protection
- **Consent Management**: User privacy controls
- **Right to Erasure**: Data deletion capabilities

### Procurement Compliance
- **Transparency Requirements**: Public data access
- **Audit Trails**: Complete activity logging
- **Data Retention**: Legal retention requirements
- **Reporting Standards**: Government reporting compliance

## Future Enhancements

### Advanced Features
- **Machine Learning**: Enhanced risk detection algorithms
- **Natural Language Processing**: Document analysis
- **Predictive Analytics**: Market trend predictions
- **Blockchain Integration**: Immutable audit trails

### Platform Extensions
- **Mobile Applications**: iOS and Android apps
- **Public APIs**: Third-party integrations
- **White-label Solutions**: Customizable deployments
- **International Expansion**: Multi-country support

## Development Roadmap

### Phase 1 (Months 1-3): MVP Development
- Core tender ingestion and storage
- Basic search and filtering
- User authentication and roles
- Simple risk detection algorithms
- Basic web interface

### Phase 2 (Months 4-6): Enhanced Features
- Advanced risk detection
- Analytics dashboard
- Alert system
- API endpoints
- Mobile-responsive design

### Phase 3 (Months 7-12): Scale and Optimize
- Performance optimization
- Advanced analytics
- Reporting system
- Microservices extraction
- Advanced monitoring

This comprehensive architecture provides a solid foundation for building a superior alternative to e-licitatie.ro while maintaining cost-effectiveness, scalability, and security. The modular design allows for incremental development and deployment, ensuring rapid time-to-market while maintaining long-term extensibility.