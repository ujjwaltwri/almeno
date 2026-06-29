import pandas as pd
import numpy as np
import os
import json
from google import genai
from tenacity import retry, wait_exponential, stop_after_attempt

# Initialize Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # Remove exact duplicate rows
    df = df.drop_duplicates()
    
    # Normalise date formats to ISO 8601
    df['date'] = pd.to_datetime(df['date'], errors='coerce', format='mixed').dt.strftime('%Y-%m-%d')
    
    # Strip currency symbols from amounts
    if df['amount'].dtype == object:
        df['amount'] = df['amount'].replace({'\$': '', ',': ''}, regex=True)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # Uppercase status values
    df['status'] = df['status'].str.upper()
    
    # Uppercase currency for consistency
    df['currency'] = df['currency'].str.upper()
    
    # Fill missing categories with 'Uncategorised'
    df['category'] = df['category'].replace('', np.nan).fillna('Uncategorised')
    
    return df

def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    df['is_anomaly'] = False
    df['anomaly_reason'] = None
    
    # Flag transactions where amount exceeds 3x the account's median as a statistical outlier
    medians = df.groupby('account_id')['amount'].transform('median')
    outlier_mask = df['amount'] > 3 * medians
    
    # Flag rows where currency is USD but the merchant is a domestic-only brand
    domestic_brands = ['SWIGGY', 'OLA', 'IRCTC']
    merchant_upper = df['merchant'].astype(str).str.upper()
    usd_domestic_mask = (df['currency'] == 'USD') & (merchant_upper.isin(domestic_brands))
    
    # Apply flags
    for idx in df[outlier_mask].index:
        df.at[idx, 'is_anomaly'] = True
        df.at[idx, 'anomaly_reason'] = "Amount > 3x account median"
        
    for idx in df[usd_domestic_mask].index:
        df.at[idx, 'is_anomaly'] = True
        reason = df.at[idx, 'anomaly_reason']
        df.at[idx, 'anomaly_reason'] = reason + "; USD domestic brand" if reason else "USD domestic brand"
        
    return df

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def call_gemini_classification(batch: str) -> str:
    if not client:
        raise Exception("Gemini API Key not set")
    prompt = f"Categorize the following transactions into one of: Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, or Other. Return ONLY a JSON list of categories corresponding to each transaction.\n\nTransactions:\n{batch}"
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text

def classify_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df['llm_category'] = None
    df['llm_raw_response'] = None
    df['llm_failed'] = False
    
    uncategorized_mask = df['category'] == 'Uncategorised'
    if not uncategorized_mask.any():
        return df
        
    uncategorized_df = df[uncategorized_mask]
    
    # Batch processing (e.g., 20 at a time)
    batch_size = 20
    for i in range(0, len(uncategorized_df), batch_size):
        batch_indices = uncategorized_df.index[i:i+batch_size]
        batch_records = df.loc[batch_indices, ['merchant', 'amount', 'notes']].to_dict('records')
        batch_str = json.dumps(batch_records)
        
        try:
            response_text = call_gemini_classification(batch_str)
            # Basic parsing, expecting a JSON array of strings
            try:
                # Clean up response if it has markdown formatting
                clean_resp = response_text.replace("```json", "").replace("```", "").strip()
                categories = json.loads(clean_resp)
                if isinstance(categories, list) and len(categories) == len(batch_indices):
                    for j, idx in enumerate(batch_indices):
                        df.at[idx, 'llm_category'] = categories[j]
                        df.at[idx, 'category'] = categories[j] # Update main category too
                else:
                    raise Exception("Output format mismatch")
            except Exception as parse_e:
                for idx in batch_indices:
                    df.at[idx, 'llm_failed'] = True
                    df.at[idx, 'llm_raw_response'] = response_text
        except Exception as e:
            # Mark batch as failed
            for idx in batch_indices:
                df.at[idx, 'llm_failed'] = True
                df.at[idx, 'llm_raw_response'] = str(e)
                
    return df

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def generate_narrative_summary(df: pd.DataFrame) -> dict:
    if not client:
        return {
            "narrative": "LLM API Key missing, could not generate summary.",
            "risk_level": "unknown"
        }
        
    summary_data = {
        "total_transactions": int(len(df)),
        "total_spend_inr": float(df[df['currency'] == 'INR']['amount'].sum()),
        "total_spend_usd": float(df[df['currency'] == 'USD']['amount'].sum()),
        "anomaly_count": int(df['is_anomaly'].sum()),
        "top_merchants": df['merchant'].value_counts().head(3).to_dict()
    }
    
    prompt = f"Analyze this transaction summary and provide a JSON response with exactly these two keys: 'narrative' (a 2-3 sentence summary of the spending patterns) and 'risk_level' (one of: low, medium, high based on anomaly count and spend).\n\nSummary data:\n{json.dumps(summary_data, indent=2)}\n\nOutput only valid JSON."
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    try:
        clean_resp = response.text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_resp)
        return {
            "narrative": parsed.get("narrative", "Generated narrative unavailable."),
            "risk_level": parsed.get("risk_level", "unknown")
        }
    except:
        return {
            "narrative": "Failed to parse LLM response.",
            "risk_level": "unknown"
        }
