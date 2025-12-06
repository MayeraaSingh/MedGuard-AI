"""
MedGuard AI - SQLAlchemy ORM Models
Phase 1: Data Layer & Input Pipeline

SQLAlchemy models for provider data, source evidence, validation runs, and review queue.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DECIMAL, TIMESTAMP, 
    ForeignKey, Index, DATE
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class ProviderBasic(Base):
    """
    Core provider information with validation confidence scores.
    """
    __tablename__ = 'provider_basic'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    degree = Column(String(20))
    
    # Professional Identifiers
    npi = Column(String(10), unique=True, nullable=False, index=True)
    license_number = Column(String(50))
    license_state = Column(String(2))
    license_issue_date = Column(DATE)
    license_expiration_date = Column(DATE)
    dea_number = Column(String(20))
    
    # Specialty & Practice
    specialty = Column(String(100), index=True)
    practice_name = Column(String(200))
    practice_type = Column(String(50))
    years_in_practice = Column(Integer)
    
    # Contact Information
    street_address = Column(String(255))
    city = Column(String(100))
    state = Column(String(2), index=True)
    zip_code = Column(String(10))
    phone = Column(String(20))
    fax = Column(String(20))
    email = Column(String(150))
    website = Column(String(255))
    
    # Education
    medical_school = Column(String(200))
    graduation_year = Column(Integer)
    
    # Additional Information
    accepts_new_patients = Column(Boolean, default=True)
    insurances_accepted = Column(Text)
    languages_spoken = Column(Text)
    
    # Confidence Scores (0.0 to 1.0)
    confidence_name = Column(DECIMAL(3, 2), default=0.50)
    confidence_npi = Column(DECIMAL(3, 2), default=0.50)
    confidence_license = Column(DECIMAL(3, 2), default=0.50)
    confidence_address = Column(DECIMAL(3, 2), default=0.50)
    confidence_phone = Column(DECIMAL(3, 2), default=0.50)
    confidence_email = Column(DECIMAL(3, 2), default=0.50)
    confidence_specialty = Column(DECIMAL(3, 2), default=0.50)
    confidence_overall = Column(DECIMAL(3, 2), default=0.50)
    
    # Validation Status
    validation_status = Column(String(50), default='pending', index=True)
    last_validation_date = Column(TIMESTAMP)
    requires_manual_review = Column(Boolean, default=False, index=True)
    flagged_reason = Column(Text)
    
    # Record Management
    record_status = Column(String(20), default='active')
    data_source = Column(String(50), default='synthetic')
    date_added = Column(TIMESTAMP, default=func.now())
    date_modified = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    # Relationships
    source_evidence = relationship("ProviderSourceEvidence", back_populates="provider", cascade="all, delete-orphan")
    review_items = relationship("ReviewQueue", back_populates="provider", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Provider(id={self.provider_id}, name={self.first_name} {self.last_name}, npi={self.npi})>"


class ProviderSourceEvidence(Base):
    """
    Stores evidence from multiple data sources for each provider field.
    Enables source comparison and confidence scoring.
    """
    __tablename__ = 'provider_source_evidence'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(String(50), ForeignKey('provider_basic.provider_id', ondelete='CASCADE'), nullable=False)
    
    # Field Information
    field_name = Column(String(100), nullable=False)
    source_value = Column(Text)
    
    # Source Information
    source_name = Column(String(100), nullable=False, index=True)
    source_url = Column(Text)
    source_confidence_weight = Column(DECIMAL(3, 2), nullable=False)
    
    # Validation Metadata
    timestamp = Column(TIMESTAMP, default=func.now())
    extraction_method = Column(String(50))
    validation_run_id = Column(Integer, ForeignKey('validation_runs.id', ondelete='SET NULL'))
    
    # Quality Indicators
    match_score = Column(DECIMAL(3, 2))
    is_primary_source = Column(Boolean, default=False)
    discrepancy_detected = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationships
    provider = relationship("ProviderBasic", back_populates="source_evidence")
    validation_run = relationship("ValidationRun", back_populates="evidence_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_provider_field', 'provider_id', 'field_name'),
    )
    
    def __repr__(self):
        return f"<Evidence(provider={self.provider_id}, field={self.field_name}, source={self.source_name})>"


class ValidationRun(Base):
    """
    Tracks validation job execution and metrics.
    """
    __tablename__ = 'validation_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Job Information
    run_id = Column(String(50), unique=True, nullable=False, index=True)
    job_type = Column(String(50), default='full_validation')
    status = Column(String(50), default='pending', index=True)
    
    # Execution Metrics
    start_time = Column(TIMESTAMP, default=func.now(), index=True)
    end_time = Column(TIMESTAMP)
    duration_seconds = Column(Integer)
    providers_processed = Column(Integer, default=0)
    providers_succeeded = Column(Integer, default=0)
    providers_failed = Column(Integer, default=0)
    
    # Quality Metrics
    avg_confidence_score = Column(DECIMAL(3, 2))
    fields_updated = Column(Integer, default=0)
    discrepancies_found = Column(Integer, default=0)
    providers_flagged = Column(Integer, default=0)
    
    # Performance Metrics (for KPI testing Phase 8)
    throughput_per_hour = Column(DECIMAL(10, 2))
    validation_accuracy = Column(DECIMAL(5, 2))
    ocr_extraction_accuracy = Column(DECIMAL(5, 2))
    
    # Configuration
    config_params = Column(Text)  # JSON string
    agents_used = Column(Text)    # Comma-separated list
    
    # Error Tracking
    error_count = Column(Integer, default=0)
    error_log = Column(Text)
    
    # Triggered By
    triggered_by = Column(String(100), default='system')
    trigger_source = Column(String(50), default='manual')
    
    # Relationships
    evidence_records = relationship("ProviderSourceEvidence", back_populates="validation_run")
    
    def __repr__(self):
        return f"<ValidationRun(id={self.run_id}, status={self.status}, processed={self.providers_processed})>"


class ReviewQueue(Base):
    """
    Manages providers requiring manual review.
    Prioritizes by impact and confidence level.
    """
    __tablename__ = 'review_queue'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(String(50), ForeignKey('provider_basic.provider_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Issue Information
    issue_type = Column(String(100), nullable=False)
    issue_severity = Column(String(20), default='medium', index=True)
    issue_description = Column(Text, nullable=False)
    
    # Affected Fields
    affected_fields = Column(Text)
    conflicting_sources = Column(Text)  # JSON array
    
    # Priority Calculation
    priority_score = Column(Integer, default=50, index=True)
    impact_level = Column(String(20), default='medium')
    
    # Resolution Status
    review_status = Column(String(50), default='pending', index=True)
    assigned_to = Column(String(100))
    resolution = Column(Text)
    resolution_date = Column(TIMESTAMP)
    
    # Timestamps
    created_date = Column(TIMESTAMP, default=func.now(), index=True)
    last_updated = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    # Actions Taken
    actions_taken = Column(Text)  # JSON array
    requires_provider_contact = Column(Boolean, default=False)
    contact_attempted = Column(Boolean, default=False)
    
    # Relationships
    provider = relationship("ProviderBasic", back_populates="review_items")
    
    def __repr__(self):
        return f"<ReviewQueue(provider={self.provider_id}, issue={self.issue_type}, priority={self.priority_score})>"


# ============================================================================
# Database initialization and utility functions
# ============================================================================

def init_database(engine):
    """
    Initialize database schema.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(engine)
    print("✓ Database schema initialized successfully")


def drop_all_tables(engine):
    """
    Drop all tables (use with caution!).
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.drop_all(engine)
    print("✓ All tables dropped")


def get_table_names():
    """
    Get list of all table names.
    
    Returns:
        List of table name strings
    """
    return [table.name for table in Base.metadata.sorted_tables]


if __name__ == "__main__":
    # Example usage
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create SQLite database
    engine = create_engine('sqlite:///medguard_test.db', echo=True)
    
    # Initialize schema
    init_database(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("\nTable names:", get_table_names())
    print("\n✓ ORM models loaded successfully")
