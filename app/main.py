import os
import shutil
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import Job, Transaction, JobSummary
from .schemas import JobResponse, JobStatusResponse, JobResultsResponse, TransactionSchema
from .tasks import process_transaction_file

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Transaction Processing Pipeline")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/jobs/upload", response_model=JobResponse)
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    job = Job(filename=file.filename, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    
    file_path = os.path.join(UPLOAD_DIR, f"{job.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    process_transaction_file.delay(job.id, file_path)
    
    return {"job_id": job.id, "status": job.status, "message": "File uploaded and job queued successfully"}

@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    response_data = {
        "job_id": job.id,
        "status": job.status,
        "filename": job.filename,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "row_count_raw": job.row_count_raw,
        "row_count_clean": job.row_count_clean,
        "error_message": job.error_message
    }
    
    if job.status == "completed" and job.summary:
        response_data["summary_stats"] = {
            "total_spend_inr": job.summary.total_spend_inr,
            "total_spend_usd": job.summary.total_spend_usd,
            "top_merchants": job.summary.top_merchants,
            "anomaly_count": job.summary.anomaly_count,
            "risk_level": job.summary.risk_level
        }
        
    return response_data

@app.get("/jobs/{job_id}/results", response_model=JobResultsResponse)
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job is not completed yet. Current status: {job.status}")
        
    transactions = db.query(Transaction).filter(Transaction.job_id == job_id).all()
    cleaned = [t for t in transactions if not t.is_anomaly]
    anomalies = [t for t in transactions if t.is_anomaly]
    
    categories = {}
    for t in transactions:
        cat = t.category or "Uncategorised"
        if t.amount:
            categories[cat] = categories.get(cat, 0) + t.amount
            
    narrative_summary = None
    if job.summary:
        narrative_summary = {
            "narrative": job.summary.narrative,
            "risk_level": job.summary.risk_level,
            "anomaly_count": job.summary.anomaly_count,
            "top_merchants": job.summary.top_merchants
        }
        
    return {
        "job_id": job.id,
        "status": job.status,
        "cleaned_transactions": cleaned,
        "flagged_anomalies": anomalies,
        "spend_breakdown": categories,
        "narrative_summary": narrative_summary
    }

@app.get("/jobs")
def list_jobs(status: str = None, db: Session = Depends(get_db)):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    jobs = query.all()
    
    return [
        {
            "job_id": j.id, 
            "status": j.status, 
            "filename": j.filename, 
            "row_count_clean": j.row_count_clean, 
            "created_at": j.created_at
        } for j in jobs
    ]
