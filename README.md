# AI-Powered Transaction Processing Pipeline

This is an asynchronous backend pipeline for processing financial transactions using FastAPI, Celery, Redis, PostgreSQL, and Google's Gemini 2.5 Flash for LLM classification and anomaly detection.

## Setup Instructions

1. **Add your API Key**: Open the `.env` file in the root directory and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

2. **Start the system**:
   The entire system (API, Celery worker, Redis, and PostgreSQL) runs in Docker. Just run:
   ```bash
   docker compose up --build
   ```

3. **Access the API Documentation**:
   Once running, you can visit the auto-generated Swagger UI docs at:
   http://localhost:8000/docs

## Example `curl` Requests

**1. Upload a CSV file**
```bash
curl -X POST "http://localhost:8000/jobs/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@transactions.csv"
```
*(This returns a `job_id` you will use in the next steps).*

**2. Check Job Status**
Replace `{job_id}` with the ID from step 1.
```bash
curl -X GET "http://localhost:8000/jobs/{job_id}/status" -H "accept: application/json"
```

**3. Get Job Results**
Once the status is "completed", you can fetch the results:
```bash
curl -X GET "http://localhost:8000/jobs/{job_id}/results" -H "accept: application/json"
```

**4. List all jobs**
```bash
curl -X GET "http://localhost:8000/jobs?status=completed" -H "accept: application/json"
```

## Architecture & Data Flow
- **API**: FastAPI receives the file upload, saves it to a shared volume, logs a `Job` in PostgreSQL, and enqueues a Celery task.
- **Queue**: Celery uses Redis as a message broker to queue the background task, returning the job ID instantly.
- **Worker**: A Celery worker dequeues the job, loads the CSV using pandas, cleans the data, runs statistical anomaly detection, and calls Gemini via the `google-genai` SDK with exponential backoff (`tenacity` library) for categorization and summarization. It then stores the structured results and status back in PostgreSQL.
- **Database**: PostgreSQL holds `jobs`, `transactions`, and `job_summaries`.
