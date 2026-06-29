import pandas as pd
import datetime
import math
from celery import shared_task
from .database import SessionLocal
from .models import Job, Transaction, JobSummary
from .services import clean_data, detect_anomalies, classify_transactions, generate_narrative_summary

@shared_task
def process_transaction_file(job_id: str, file_path: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return "Job not found"
    
    try:
        job.status = "processing"
        db.commit()
        
        # Load CSV
        df = pd.read_csv(file_path)
        job.row_count_raw = len(df)
        
        # 1. Clean Data
        df = clean_data(df)
        job.row_count_clean = len(df)
        
        # 2. Anomaly Detection
        df = detect_anomalies(df)
        
        # 3. LLM Classification
        df = classify_transactions(df)
        
        # Save transactions to DB
        for _, row in df.iterrows():
            # Handle NaN values
            def clean_val(val):
                if pd.isna(val):
                    return None
                return val

            txn = Transaction(
                job_id=job.id,
                txn_id=clean_val(row.get('txn_id')),
                date=clean_val(row.get('date')),
                merchant=clean_val(row.get('merchant')),
                amount=clean_val(row.get('amount')),
                currency=clean_val(row.get('currency')),
                status=clean_val(row.get('status')),
                category=clean_val(row.get('category')),
                account_id=clean_val(row.get('account_id')),
                is_anomaly=bool(row.get('is_anomaly', False)),
                anomaly_reason=clean_val(row.get('anomaly_reason')),
                llm_category=clean_val(row.get('llm_category')),
                llm_raw_response=clean_val(row.get('llm_raw_response')),
                llm_failed=bool(row.get('llm_failed', False))
            )
            db.add(txn)
        db.commit()
        
        # 4. LLM Narrative Summary
        summary_result = generate_narrative_summary(df)
        
        total_inr = float(df[df['currency'] == 'INR']['amount'].sum())
        total_usd = float(df[df['currency'] == 'USD']['amount'].sum())
        top_merchants = df['merchant'].value_counts().head(3).to_dict()
        
        summary = JobSummary(
            job_id=job.id,
            total_spend_inr=0.0 if math.isnan(total_inr) else total_inr,
            total_spend_usd=0.0 if math.isnan(total_usd) else total_usd,
            top_merchants=top_merchants,
            anomaly_count=int(df['is_anomaly'].sum()),
            narrative=summary_result.get('narrative'),
            risk_level=summary_result.get('risk_level')
        )
        db.add(summary)
        
        # Update job status
        job.status = "completed"
        job.completed_at = datetime.datetime.utcnow()
        db.commit()
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.datetime.utcnow()
        db.commit()
        raise e
    finally:
        db.close()
