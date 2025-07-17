# Database Schema Design for Romanian Public Procurement Platform

## Database Selection Rationale

**Primary Database: PostgreSQL 15+**
- **JSONB Support**: Flexible schema for varying tender document structures
- **Full-Text Search**: Built-in search capabilities for tender documents
- **ACID Compliance**: Critical for financial and procurement data integrity
- **Performance**: Excellent query optimization and indexing
- **Scalability**: Supports read replicas and horizontal scaling

## Core Database Schema

### 1. User Management Schema

```sql
-- Users table - Core user information
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0
);

-- User roles and permissions
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User role assignments
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

-- User profiles - Extended user information
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    company_name VARCHAR(255),
    company_cui VARCHAR(20), -- Romanian company identifier
    company_address TEXT,
    phone VARCHAR(20),
    subscription_type VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    notification_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User sessions for tracking active sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE
);
```

### 2. Tender Data Schema

```sql
-- Contracting authorities/organizations
CREATE TABLE contracting_authorities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cui VARCHAR(20) UNIQUE, -- Romanian company identifier
    address TEXT,
    county VARCHAR(50),
    city VARCHAR(100),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    website VARCHAR(255),
    authority_type VARCHAR(50), -- central, local, utility, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- CPV codes (Common Procurement Vocabulary)
CREATE TABLE cpv_codes (
    code VARCHAR(10) PRIMARY KEY,
    description TEXT NOT NULL,
    parent_code VARCHAR(10),
    level INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Main tenders table
CREATE TABLE tenders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system VARCHAR(50) NOT NULL, -- SICAP, ANRMAP, EU_TED, etc.
    external_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    contracting_authority_id INTEGER REFERENCES contracting_authorities(id),
    cpv_code VARCHAR(10) REFERENCES cpv_codes(code),
    
    -- Tender details
    tender_type VARCHAR(50) NOT NULL, -- open, restricted, negotiated, etc.
    procedure_type VARCHAR(50), -- supplies, services, works
    estimated_value DECIMAL(15,2),
    currency VARCHAR(3) DEFAULT 'RON',
    
    -- Important dates
    publication_date TIMESTAMP WITH TIME ZONE,
    submission_deadline TIMESTAMP WITH TIME ZONE,
    opening_date TIMESTAMP WITH TIME ZONE,
    contract_start_date TIMESTAMP WITH TIME ZONE,
    contract_end_date TIMESTAMP WITH TIME ZONE,
    
    -- Status tracking
    status VARCHAR(50) NOT NULL, -- published, active, closed, awarded, cancelled
    
    -- Flexible data storage for source-specific fields
    raw_data JSONB DEFAULT '{}',
    processed_data JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(source_system, external_id)
);

-- Tender documents (specifications, annexes, etc.)
CREATE TABLE tender_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID REFERENCES tenders(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL, -- specification, annex, clarification
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size BIGINT,
    file_hash VARCHAR(64),
    mime_type VARCHAR(100),
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    extracted_text TEXT, -- For full-text search
    metadata JSONB DEFAULT '{}'
);

-- Companies/bidders
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cui VARCHAR(20) UNIQUE, -- Romanian company identifier
    registration_number VARCHAR(50),
    address TEXT,
    county VARCHAR(50),
    city VARCHAR(100),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    company_type VARCHAR(50), -- SRL, SA, PFA, etc.
    company_size VARCHAR(20), -- micro, small, medium, large
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tender bids/offers
CREATE TABLE tender_bids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID REFERENCES tenders(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(id),
    
    -- Bid details
    bid_amount DECIMAL(15,2),
    currency VARCHAR(3) DEFAULT 'RON',
    bid_date TIMESTAMP WITH TIME ZONE,
    
    -- Bid status
    status VARCHAR(50) NOT NULL, -- submitted, evaluated, winner, rejected
    is_winner BOOLEAN DEFAULT false,
    
    -- Additional bid information
    execution_period_days INTEGER,
    bid_documents JSONB DEFAULT '{}',
    evaluation_score DECIMAL(5,2),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tender awards/contracts
CREATE TABLE tender_awards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID REFERENCES tenders(id) ON DELETE CASCADE,
    winning_bid_id UUID REFERENCES tender_bids(id),
    company_id INTEGER REFERENCES companies(id),
    
    -- Award details
    awarded_amount DECIMAL(15,2),
    currency VARCHAR(3) DEFAULT 'RON',
    award_date TIMESTAMP WITH TIME ZONE,
    contract_number VARCHAR(100),
    
    -- Contract details
    contract_start_date TIMESTAMP WITH TIME ZONE,
    contract_end_date TIMESTAMP WITH TIME ZONE,
    contract_value DECIMAL(15,2),
    
    -- Status
    status VARCHAR(50) NOT NULL, -- awarded, signed, active, completed, cancelled
    
    -- Additional information
    award_criteria JSONB DEFAULT '{}',
    award_justification TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3. Risk Analysis Schema

```sql
-- Risk analysis configurations
CREATE TABLE risk_algorithms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    algorithm_type VARCHAR(50) NOT NULL, -- single_bidder, price_anomaly, frequency, etc.
    parameters JSONB DEFAULT '{}',
    weight DECIMAL(3,2) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk scores for tenders
CREATE TABLE tender_risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID REFERENCES tenders(id) ON DELETE CASCADE,
    
    -- Overall risk assessment
    overall_risk_score DECIMAL(5,2) NOT NULL,
    risk_level VARCHAR(20) NOT NULL, -- low, medium, high, critical
    
    -- Individual risk components
    single_bidder_risk DECIMAL(5,2) DEFAULT 0,
    price_anomaly_risk DECIMAL(5,2) DEFAULT 0,
    frequency_risk DECIMAL(5,2) DEFAULT 0,
    geographic_risk DECIMAL(5,2) DEFAULT 0,
    
    -- Risk analysis details
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analysis_version VARCHAR(20),
    detailed_analysis JSONB DEFAULT '{}',
    
    -- Risk flags
    risk_flags JSONB DEFAULT '[]',
    auto_generated BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk alerts for users
CREATE TABLE risk_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    tender_id UUID REFERENCES tenders(id) ON DELETE CASCADE,
    risk_score_id UUID REFERENCES tender_risk_scores(id),
    
    -- Alert details
    alert_type VARCHAR(50) NOT NULL, -- new_risk, risk_change, threshold_breach
    alert_level VARCHAR(20) NOT NULL, -- low, medium, high, critical
    title VARCHAR(255) NOT NULL,
    message TEXT,
    
    -- Alert status
    status VARCHAR(20) DEFAULT 'unread', -- unread, read, dismissed
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- Delivery tracking
    delivery_method VARCHAR(20) DEFAULT 'in_app', -- in_app, email, both
    email_sent BOOLEAN DEFAULT false,
    email_sent_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk pattern analysis
CREATE TABLE risk_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(50) NOT NULL, -- company_monopoly, location_clustering, etc.
    pattern_name VARCHAR(255) NOT NULL,
    
    -- Pattern details
    affected_tenders UUID[] NOT NULL,
    affected_companies INTEGER[] NOT NULL,
    pattern_score DECIMAL(5,2) NOT NULL,
    
    -- Pattern metadata
    discovery_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    pattern_data JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 4. Analytics and Monitoring Schema

```sql
-- User activity tracking
CREATE TABLE user_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Activity details
    action_type VARCHAR(50) NOT NULL, -- view, search, download, alert_create
    resource_type VARCHAR(50), -- tender, company, report
    resource_id VARCHAR(255),
    
    -- Request details
    ip_address INET,
    user_agent TEXT,
    request_path VARCHAR(500),
    request_method VARCHAR(10),
    
    -- Response details
    response_status INTEGER,
    response_time_ms INTEGER,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System metrics
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type VARCHAR(50) NOT NULL, -- api_performance, data_quality, system_health
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,2) NOT NULL,
    metric_unit VARCHAR(20),
    
    -- Dimensions
    dimensions JSONB DEFAULT '{}',
    
    -- Timestamp
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- Data ingestion logs
CREATE TABLE data_ingestion_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system VARCHAR(50) NOT NULL,
    job_id VARCHAR(100),
    
    -- Job details
    job_type VARCHAR(50) NOT NULL, -- full_sync, incremental, real_time
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Results
    status VARCHAR(20) NOT NULL, -- running, completed, failed, partial
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User saved searches and alerts
CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Search details
    search_name VARCHAR(255) NOT NULL,
    search_query JSONB NOT NULL,
    search_filters JSONB DEFAULT '{}',
    
    -- Alert configuration
    alert_enabled BOOLEAN DEFAULT false,
    alert_frequency VARCHAR(20) DEFAULT 'daily', -- real_time, daily, weekly
    last_alert_sent TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Database Indexes for Performance

```sql
-- Core indexes for frequent queries
CREATE INDEX idx_tenders_status ON tenders(status);
CREATE INDEX idx_tenders_publication_date ON tenders(publication_date);
CREATE INDEX idx_tenders_contracting_authority ON tenders(contracting_authority_id);
CREATE INDEX idx_tenders_cpv_code ON tenders(cpv_code);
CREATE INDEX idx_tenders_source_system ON tenders(source_system);
CREATE INDEX idx_tenders_estimated_value ON tenders(estimated_value);

-- Composite indexes for complex queries
CREATE INDEX idx_tenders_status_date ON tenders(status, publication_date);
CREATE INDEX idx_tenders_authority_date ON tenders(contracting_authority_id, publication_date);

-- Full-text search indexes
CREATE INDEX idx_tenders_title_fts ON tenders USING GIN (to_tsvector('romanian', title));
CREATE INDEX idx_tenders_description_fts ON tenders USING GIN (to_tsvector('romanian', description));
CREATE INDEX idx_tender_documents_text_fts ON tender_documents USING GIN (to_tsvector('romanian', extracted_text));

-- JSONB indexes for flexible queries
CREATE INDEX idx_tenders_raw_data ON tenders USING GIN (raw_data);
CREATE INDEX idx_tenders_processed_data ON tenders USING GIN (processed_data);

-- Risk analysis indexes
CREATE INDEX idx_risk_scores_tender ON tender_risk_scores(tender_id);
CREATE INDEX idx_risk_scores_level ON tender_risk_scores(risk_level);
CREATE INDEX idx_risk_scores_overall ON tender_risk_scores(overall_risk_score);
CREATE INDEX idx_risk_scores_date ON tender_risk_scores(analysis_date);

-- User activity indexes
CREATE INDEX idx_user_activity_user ON user_activity(user_id);
CREATE INDEX idx_user_activity_created ON user_activity(created_at);
CREATE INDEX idx_user_activity_action ON user_activity(action_type);

-- Companies and bids indexes
CREATE INDEX idx_companies_cui ON companies(cui);
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_tender_bids_tender ON tender_bids(tender_id);
CREATE INDEX idx_tender_bids_company ON tender_bids(company_id);
CREATE INDEX idx_tender_bids_winner ON tender_bids(is_winner);
```

## Data Partitioning Strategy

```sql
-- Partition tenders by publication date (monthly partitions)
CREATE TABLE tenders_template (LIKE tenders INCLUDING ALL);

-- Example partition for 2024-01
CREATE TABLE tenders_2024_01 PARTITION OF tenders
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Partition user activity by date (daily partitions for recent data)
CREATE TABLE user_activity_template (LIKE user_activity INCLUDING ALL);

-- Example partition for recent activity
CREATE TABLE user_activity_2024_01_15 PARTITION OF user_activity
FOR VALUES FROM ('2024-01-15') TO ('2024-01-16');
```

## Data Relationships and Constraints

### Key Relationships:
1. **Users → User Profiles**: One-to-one relationship for extended user information
2. **Users → Saved Searches**: One-to-many for user search preferences
3. **Tenders → Tender Bids**: One-to-many for bid submissions
4. **Tenders → Risk Scores**: One-to-many for risk analysis history
5. **Companies → Tender Bids**: One-to-many for company bidding history
6. **Contracting Authorities → Tenders**: One-to-many for authority procurement

### Data Integrity Rules:
- **Cascading Deletes**: User deletion removes all related data
- **Soft Deletes**: Tender data marked as deleted but preserved for audit
- **Unique Constraints**: Prevent duplicate external IDs within source systems
- **Check Constraints**: Validate data ranges and business rules

## Performance Considerations

### Query Optimization:
- **Materialized Views**: Pre-computed aggregations for dashboard queries
- **Partial Indexes**: Indexes on filtered data subsets
- **Query Plans**: Regular analysis and optimization of slow queries
- **Connection Pooling**: Efficient database connection management

### Scaling Strategies:
- **Read Replicas**: Separate instances for read-heavy operations
- **Sharding**: Horizontal partitioning by geographical regions
- **Archiving**: Move old data to separate archive tables
- **Compression**: Table compression for historical data

## Security Considerations

### Data Protection:
- **Row-Level Security**: User-specific data access controls
- **Column Encryption**: Sensitive data encrypted at rest
- **Audit Trail**: Complete logging of data modifications
- **Data Anonymization**: PII protection for analytics

### Access Control:
- **Role-Based Permissions**: Granular access control
- **Connection Security**: SSL/TLS for all database connections
- **SQL Injection Prevention**: Parameterized queries only
- **Regular Backups**: Encrypted backup strategy

This database schema provides a robust foundation for the procurement platform, supporting both business intelligence features and transparency requirements while maintaining high performance and security standards.