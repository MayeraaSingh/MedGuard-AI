-- MedGuard AI - Provider Database Schema
-- Phase 1: Data Layer & Input Pipeline
-- Database: SQLite/PostgreSQL compatible schema

-- ============================================================================
-- TABLE 1: provider_basic
-- Core provider information with validation confidence scores
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_basic (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Personal Information
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    degree VARCHAR(20),
    
    -- Professional Identifiers
    npi VARCHAR(10) UNIQUE NOT NULL,
    license_number VARCHAR(50),
    license_state VARCHAR(2),
    license_issue_date DATE,
    license_expiration_date DATE,
    dea_number VARCHAR(20),
    
    -- Specialty & Practice
    specialty VARCHAR(100),
    practice_name VARCHAR(200),
    practice_type VARCHAR(50),
    years_in_practice INTEGER,
    
    -- Contact Information
    street_address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    phone VARCHAR(20),
    fax VARCHAR(20),
    email VARCHAR(150),
    website VARCHAR(255),
    
    -- Education
    medical_school VARCHAR(200),
    graduation_year INTEGER,
    
    -- Additional Information
    accepts_new_patients BOOLEAN DEFAULT TRUE,
    insurances_accepted TEXT,
    languages_spoken TEXT,
    
    -- Confidence Scores (0.0 to 1.0)
    confidence_name DECIMAL(3,2) DEFAULT 0.50,
    confidence_npi DECIMAL(3,2) DEFAULT 0.50,
    confidence_license DECIMAL(3,2) DEFAULT 0.50,
    confidence_address DECIMAL(3,2) DEFAULT 0.50,
    confidence_phone DECIMAL(3,2) DEFAULT 0.50,
    confidence_email DECIMAL(3,2) DEFAULT 0.50,
    confidence_specialty DECIMAL(3,2) DEFAULT 0.50,
    confidence_overall DECIMAL(3,2) DEFAULT 0.50,
    
    -- Validation Status
    validation_status VARCHAR(50) DEFAULT 'pending', -- pending, validated, flagged, failed
    last_validation_date TIMESTAMP,
    requires_manual_review BOOLEAN DEFAULT FALSE,
    flagged_reason TEXT,
    
    -- Record Management
    record_status VARCHAR(20) DEFAULT 'active', -- active, inactive, archived
    data_source VARCHAR(50) DEFAULT 'synthetic', -- synthetic, ocr, manual, api
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_npi (npi),
    INDEX idx_license (license_number, license_state),
    INDEX idx_specialty (specialty),
    INDEX idx_state (state),
    INDEX idx_validation_status (validation_status),
    INDEX idx_requires_review (requires_manual_review)
);


-- ============================================================================
-- TABLE 2: provider_source_evidence
-- Stores evidence from multiple data sources for each provider field
-- Enables source comparison and confidence scoring
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_source_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id VARCHAR(50) NOT NULL,
    
    -- Field Information
    field_name VARCHAR(100) NOT NULL, -- e.g., 'phone', 'address', 'specialty'
    source_value TEXT, -- The value found from this source
    
    -- Source Information
    source_name VARCHAR(100) NOT NULL, -- e.g., 'npi_registry', 'google_maps', 'ocr', 'practice_website'
    source_url TEXT, -- URL or reference where data was found
    source_confidence_weight DECIMAL(3,2) NOT NULL, -- Predefined weight: 0.50-0.95
    
    -- Validation Metadata
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extraction_method VARCHAR(50), -- 'api', 'scraping', 'ocr', 'manual'
    validation_run_id INTEGER, -- Links to validation_runs table
    
    -- Quality Indicators
    match_score DECIMAL(3,2), -- Fuzzy match score if applicable
    is_primary_source BOOLEAN DEFAULT FALSE, -- Is this the authoritative source?
    discrepancy_detected BOOLEAN DEFAULT FALSE,
    notes TEXT,
    
    -- Foreign Key
    FOREIGN KEY (provider_id) REFERENCES provider_basic(provider_id) ON DELETE CASCADE,
    FOREIGN KEY (validation_run_id) REFERENCES validation_runs(id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_provider_field (provider_id, field_name),
    INDEX idx_source_name (source_name),
    INDEX idx_validation_run (validation_run_id)
);


-- ============================================================================
-- TABLE 3: validation_runs
-- Tracks validation job execution and metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS validation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Job Information
    run_id VARCHAR(50) UNIQUE NOT NULL, -- UUID for tracking
    job_type VARCHAR(50) DEFAULT 'full_validation', -- full_validation, ocr_extraction, enrichment_only
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    
    -- Execution Metrics
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    providers_processed INTEGER DEFAULT 0,
    providers_succeeded INTEGER DEFAULT 0,
    providers_failed INTEGER DEFAULT 0,
    
    -- Quality Metrics
    avg_confidence_score DECIMAL(3,2),
    fields_updated INTEGER DEFAULT 0,
    discrepancies_found INTEGER DEFAULT 0,
    providers_flagged INTEGER DEFAULT 0,
    
    -- Performance Metrics (for KPI testing Phase 8)
    throughput_per_hour DECIMAL(10,2), -- Providers validated per hour
    validation_accuracy DECIMAL(5,2), -- Percentage of correct validations
    ocr_extraction_accuracy DECIMAL(5,2), -- OCR accuracy percentage
    
    -- Configuration
    config_params TEXT, -- JSON string of run configuration
    agents_used TEXT, -- Comma-separated list of agents
    
    -- Error Tracking
    error_count INTEGER DEFAULT 0,
    error_log TEXT,
    
    -- Triggered By
    triggered_by VARCHAR(100) DEFAULT 'system', -- user email or 'system'
    trigger_source VARCHAR(50) DEFAULT 'manual', -- manual, scheduled, api
    
    -- Indexes
    INDEX idx_run_id (run_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time)
);


-- ============================================================================
-- TABLE 4: review_queue
-- Manages providers requiring manual review
-- Prioritizes by impact and confidence level
-- ============================================================================

CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id VARCHAR(50) NOT NULL,
    
    -- Issue Information
    issue_type VARCHAR(100) NOT NULL, -- 'phone_mismatch', 'address_invalid', 'license_expired', 'fraud_suspected'
    issue_severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    issue_description TEXT NOT NULL,
    
    -- Affected Fields
    affected_fields TEXT, -- Comma-separated list of field names
    conflicting_sources TEXT, -- JSON array of conflicting source evidence
    
    -- Priority Calculation
    priority_score INTEGER DEFAULT 50, -- 0-100, calculated based on severity and impact
    impact_level VARCHAR(20) DEFAULT 'medium', -- low, medium, high
    
    -- Resolution Status
    review_status VARCHAR(50) DEFAULT 'pending', -- pending, in_review, resolved, escalated
    assigned_to VARCHAR(100), -- User email or ID
    resolution TEXT,
    resolution_date TIMESTAMP,
    
    -- Timestamps
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Actions Taken
    actions_taken TEXT, -- JSON array of actions
    requires_provider_contact BOOLEAN DEFAULT FALSE,
    contact_attempted BOOLEAN DEFAULT FALSE,
    
    -- Foreign Key
    FOREIGN KEY (provider_id) REFERENCES provider_basic(provider_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_provider_id (provider_id),
    INDEX idx_review_status (review_status),
    INDEX idx_priority_score (priority_score DESC),
    INDEX idx_issue_severity (issue_severity),
    INDEX idx_created_date (created_date)
);


-- ============================================================================
-- HELPER VIEWS
-- Useful views for querying and reporting
-- ============================================================================

-- View: High Priority Review Items
CREATE VIEW IF NOT EXISTS vw_high_priority_reviews AS
SELECT 
    rq.id,
    rq.provider_id,
    pb.first_name,
    pb.last_name,
    pb.specialty,
    rq.issue_type,
    rq.issue_severity,
    rq.priority_score,
    rq.created_date,
    rq.review_status
FROM review_queue rq
JOIN provider_basic pb ON rq.provider_id = pb.provider_id
WHERE rq.review_status = 'pending'
  AND rq.priority_score >= 70
ORDER BY rq.priority_score DESC, rq.created_date ASC;


-- View: Provider Validation Summary
CREATE VIEW IF NOT EXISTS vw_provider_validation_summary AS
SELECT 
    pb.provider_id,
    pb.first_name,
    pb.last_name,
    pb.specialty,
    pb.state,
    pb.confidence_overall,
    pb.validation_status,
    pb.requires_manual_review,
    COUNT(DISTINCT pse.source_name) as source_count,
    pb.last_validation_date
FROM provider_basic pb
LEFT JOIN provider_source_evidence pse ON pb.provider_id = pse.provider_id
GROUP BY pb.provider_id;


-- View: Validation Run Statistics
CREATE VIEW IF NOT EXISTS vw_validation_stats AS
SELECT 
    run_id,
    job_type,
    status,
    start_time,
    duration_seconds,
    providers_processed,
    providers_succeeded,
    providers_failed,
    avg_confidence_score,
    throughput_per_hour,
    validation_accuracy,
    ocr_extraction_accuracy
FROM validation_runs
ORDER BY start_time DESC;


-- ============================================================================
-- TRIGGERS
-- Automatic timestamp updates and data integrity
-- ============================================================================

-- Trigger: Update modified timestamp on provider_basic
CREATE TRIGGER IF NOT EXISTS trg_update_provider_timestamp
AFTER UPDATE ON provider_basic
FOR EACH ROW
BEGIN
    UPDATE provider_basic 
    SET date_modified = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;


-- Trigger: Update review queue timestamp
CREATE TRIGGER IF NOT EXISTS trg_update_review_queue_timestamp
AFTER UPDATE ON review_queue
FOR EACH ROW
BEGIN
    UPDATE review_queue 
    SET last_updated = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;


-- ============================================================================
-- SAMPLE DATA QUERIES
-- Example queries for common operations
-- ============================================================================

-- Get all providers requiring manual review with their issues
-- SELECT pb.*, rq.issue_type, rq.issue_description, rq.priority_score
-- FROM provider_basic pb
-- JOIN review_queue rq ON pb.provider_id = rq.provider_id
-- WHERE pb.requires_manual_review = TRUE
-- ORDER BY rq.priority_score DESC;

-- Get all source evidence for a specific provider
-- SELECT * FROM provider_source_evidence
-- WHERE provider_id = '9999123456'
-- ORDER BY field_name, source_confidence_weight DESC;

-- Get validation run performance metrics
-- SELECT 
--     run_id,
--     providers_processed,
--     duration_seconds,
--     ROUND(providers_processed * 3600.0 / duration_seconds, 2) as throughput_per_hour,
--     avg_confidence_score
-- FROM validation_runs
-- WHERE status = 'completed'
-- ORDER BY start_time DESC;
