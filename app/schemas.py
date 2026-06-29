from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    row_count_raw: Optional[int] = None
    row_count_clean: Optional[int] = None
    error_message: Optional[str] = None
    summary_stats: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class TransactionSchema(BaseModel):
    txn_id: Optional[str]
    date: Optional[str]
    merchant: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    status: Optional[str]
    category: Optional[str]
    account_id: Optional[str]
    is_anomaly: bool
    anomaly_reason: Optional[str]
    llm_category: Optional[str]

    class Config:
        from_attributes = True

class JobResultsResponse(BaseModel):
    job_id: str
    status: str
    cleaned_transactions: List[TransactionSchema]
    flagged_anomalies: List[TransactionSchema]
    spend_breakdown: Dict[str, float]
    narrative_summary: Optional[Dict[str, Any]]
