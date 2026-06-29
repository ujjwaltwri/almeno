from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
import datetime
import uuid
from .database import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending") # pending, processing, completed, failed
    row_count_raw = Column(Integer, nullable=True)
    row_count_clean = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    transactions = relationship("Transaction", back_populates="job", cascade="all, delete-orphan")
    summary = relationship("JobSummary", back_populates="job", uselist=False, cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    txn_id = Column(String, nullable=True)
    date = Column(String, nullable=True) # Normalized to ISO 8601
    merchant = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    status = Column(String, nullable=True)
    category = Column(String, nullable=True)
    account_id = Column(String, nullable=True)
    
    is_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(String, nullable=True)
    
    llm_category = Column(String, nullable=True)
    llm_raw_response = Column(String, nullable=True)
    llm_failed = Column(Boolean, default=False)

    job = relationship("Job", back_populates="transactions")

class JobSummary(Base):
    __tablename__ = "job_summaries"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), unique=True)
    total_spend_inr = Column(Float, default=0.0)
    total_spend_usd = Column(Float, default=0.0)
    top_merchants = Column(JSON, nullable=True)
    anomaly_count = Column(Integer, default=0)
    narrative = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)

    job = relationship("Job", back_populates="summary")
