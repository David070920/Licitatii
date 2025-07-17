-- Database initialization script for Romanian Public Procurement Platform

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS procurement_platform;

-- Connect to the database
\c procurement_platform;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create initial roles
INSERT INTO roles (name, description, permissions) VALUES 
('anonymous', 'Anonymous User', '["view_public_tenders", "view_public_statistics", "view_risk_transparency"]'),
('citizen', 'Registered Citizen', '["view_public_tenders", "view_public_statistics", "view_risk_transparency", "create_alerts", "save_searches", "comment_tenders"]'),
('business_basic', 'Business User - Basic', '["view_public_tenders", "view_private_tenders", "advanced_search", "create_alerts", "save_searches", "basic_analytics", "export_data_limited"]'),
('business_premium', 'Business User - Premium', '["view_public_tenders", "view_private_tenders", "advanced_search", "create_alerts", "save_searches", "full_analytics", "export_data_unlimited", "api_access", "competitor_analysis", "custom_reports"]'),
('journalist', 'Journalist', '["view_public_tenders", "view_transparency_data", "investigation_tools", "bulk_data_export", "api_access", "advanced_risk_analysis"]'),
('admin', 'Administrator', '["user_management", "content_moderation", "system_monitoring", "data_management", "report_generation"]'),
('super_admin', 'Super Administrator', '["*"]')
ON CONFLICT (name) DO NOTHING;

-- Create sample CPV codes
INSERT INTO cpv_codes (code, description, parent_code, level) VALUES
('45000000', 'Construction work', NULL, 1),
('45100000', 'Site preparation', '45000000', 2),
('45200000', 'Building construction work', '45000000', 2),
('48000000', 'Software package and information systems', NULL, 1),
('48100000', 'Software package', '48000000', 2),
('48200000', 'Software documentation', '48000000', 2),
('79000000', 'Business services: law, marketing, consulting, recruitment, printing and security', NULL, 1),
('79100000', 'Legal services', '79000000', 2),
('79200000', 'Accounting, bookkeeping and auditing services', '79000000', 2),
('50000000', 'Repair and maintenance services', NULL, 1),
('50100000', 'Motor vehicle repair and maintenance services', '50000000', 2),
('50200000', 'Land transport vehicle repair and maintenance services', '50000000', 2)
ON CONFLICT (code) DO NOTHING;

-- Create sample contracting authorities
INSERT INTO contracting_authorities (name, cui, address, county, city, contact_email, authority_type) VALUES
('Ministry of Health', 'RO12345678', 'Str. Cristian Popisteanu 1-3, Sector 1', 'Bucharest', 'Bucharest', 'contact@ms.ro', 'central'),
('Ministry of Transport', 'RO87654321', 'Bd. Dinicu Golescu 38, Sector 1', 'Bucharest', 'Bucharest', 'contact@mt.ro', 'central'),
('Bucharest City Hall', 'RO11223344', 'Bd. Regina Elisabeta 47, Sector 3', 'Bucharest', 'Bucharest', 'contact@pmb.ro', 'local'),
('Cluj County Council', 'RO44332211', 'Str. Memorandumului 21', 'Cluj', 'Cluj-Napoca', 'contact@cjcluj.ro', 'local'),
('Timis County Council', 'RO55667788', 'Bd. Revolutiei 1989 nr. 15', 'Timis', 'Timisoara', 'contact@cjtimis.ro', 'local')
ON CONFLICT (cui) DO NOTHING;

-- Create sample companies
INSERT INTO companies (name, cui, address, county, city, company_type, company_size) VALUES
('SC Tech Solutions SRL', 'RO98765432', 'Str. Victoriei 123, Sector 1', 'Bucharest', 'Bucharest', 'SRL', 'medium'),
('SC Construction Plus SA', 'RO12398765', 'Bd. Unirii 45, Sector 3', 'Bucharest', 'Bucharest', 'SA', 'large'),
('SC IT Services SRL', 'RO56789012', 'Str. Republicii 67', 'Cluj', 'Cluj-Napoca', 'SRL', 'small'),
('SC Consulting Pro SRL', 'RO34567890', 'Bd. Libertatii 89', 'Timis', 'Timisoara', 'SRL', 'medium'),
('SC Medical Equipment SA', 'RO78901234', 'Str. Mihai Viteazul 34', 'Bucharest', 'Bucharest', 'SA', 'large')
ON CONFLICT (cui) DO NOTHING;

-- Create sample risk algorithms
INSERT INTO risk_algorithms (name, description, algorithm_type, parameters, weight, is_active) VALUES
('Single Bidder Detection', 'Detects tenders with only one bidder', 'single_bidder', '{"threshold": 1}', 1.0, true),
('Price Anomaly Detection', 'Identifies unusual pricing patterns', 'price_anomaly', '{"z_score_threshold": 2.5}', 0.8, true),
('Frequent Winner Analysis', 'Analyzes patterns of frequent winners', 'frequency', '{"win_rate_threshold": 0.7}', 0.6, true),
('Geographic Clustering', 'Detects geographic clustering anomalies', 'geographic', '{"cluster_threshold": 0.8}', 0.7, true)
ON CONFLICT (name) DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tenders_gin_title ON tenders USING gin(to_tsvector('romanian', title));
CREATE INDEX IF NOT EXISTS idx_tenders_gin_description ON tenders USING gin(to_tsvector('romanian', description));
CREATE INDEX IF NOT EXISTS idx_tender_documents_gin_text ON tender_documents USING gin(to_tsvector('romanian', extracted_text));

-- Create views for common queries
CREATE OR REPLACE VIEW tender_summary AS
SELECT 
    t.id,
    t.title,
    t.estimated_value,
    t.currency,
    t.publication_date,
    t.status,
    ca.name as contracting_authority_name,
    cpv.description as cpv_description,
    trs.overall_risk_score,
    trs.risk_level
FROM tenders t
LEFT JOIN contracting_authorities ca ON t.contracting_authority_id = ca.id
LEFT JOIN cpv_codes cpv ON t.cpv_code = cpv.code
LEFT JOIN tender_risk_scores trs ON t.id = trs.tender_id;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenders_updated_at BEFORE UPDATE ON tenders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;