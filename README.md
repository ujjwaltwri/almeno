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

![Architecture Diagram](almeno.svg)

- **API**: FastAPI receives the file upload, saves it to a shared volume, logs a `Job` in PostgreSQL, and enqueues a Celery task.
- **Queue**: Celery uses Redis as a message broker to queue the background task, returning the job ID instantly.
- **Worker**: A Celery worker dequeues the job, loads the CSV using pandas, cleans the data, runs statistical anomaly detection, and calls Gemini via the `google-genai` SDK with exponential backoff (`tenacity` library) for categorization and summarization. It then stores the structured results and status back in PostgreSQL.
- **Database**: PostgreSQL holds `jobs`, `transactions`, and `job_summaries`.

## Bottlenecks & Scaling (100x Traffic)
- **The Breaking Point**: If traffic scaled 100x tomorrow, the single Celery worker would quickly become backlogged, delaying processing. Additionally, the PostgreSQL database could hit connection limits if the API handles thousands of concurrent polling requests. The shared local volume (`/uploads`) would also fail if we deployed across multiple servers.
- **The Next Iteration**: 
  - **Workers**: Scale horizontally by adding dozens of Celery worker nodes.
  - **Storage**: Move from a local shared volume to cloud object storage (like AWS S3) for the uploaded CSVs.
  - **Database**: Implement a connection pooler like `PgBouncer` in front of PostgreSQL to handle thousands of API polling connections safely.
  - **Broker**: Potentially upgrade Redis to a more robust message queue like RabbitMQ or Kafka for better durability at enterprise scale.

## Assignment Submission Links
- **Technical Review Video**: 
- **High-Level Diagram**: [Public draw.io Link](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&dark=auto#R%3Cmxfile%3E%3Cdiagram%20name%3D%22Page-1%22%20id%3D%22VkFwjUBgWxdA8WAn76fI%22%3E7V1Zd6M4Fv41PqfyEB8Wg%2B3H2FmmumtJl2tS009zZKPYVGFwA84yv34kJGFJCAQOXqqKxCcxQhvSvd%2Bne7XQs6frl7sYbFYfIw8GPcvwXnr2dc%2ByRmMD%2FcUBryTANU0SsIx9jwRxATP%2Ff5AG0nTLre%2FBRIiYRlGQ%2BhsxcBGFIVykQhiI4%2BhZjPYYBWKpG7CEhYDZAgTF0G%2B%2Bl67oY1nDXfi%2FoL9csZJNd0zurAGLTJ8kWQEveuaC7JuePY2jKCXf1i9TGOC2Y%2B1C0t2W3M0rFsMwVST4dwLjz%2FPvuE0sIwBz1C1ZJFo7GK%2BB712DFNDg4aRnuT3LRg1vo69G9nH%2F2eLqTTwcL7%2Fq2VfC3ccgel6sQIxL%2Bnrdc6YhS08%2BTvYxruGjH0LcEulrgPoU90aMuy4AsZ%2B%2ByulQcJKgNNlXHz8kSuCjNsCl249jdGOapHH0A5IQ9JOHXD6TvrqyNi%2B4wuVZg40v5Duft5PvcxT%2FgLFY5Zay9uZijR%2FnrWQLX1IYhyCQ6txO5kkaxVjT%2BLw9z2uYd5lkfYowRkh3sQK86zkT%2FD8LuUV%2Fp0SSnOsLHIQKJZ9cxKQ8bkGSXt2%2FR7mwb5Yxg%2FETytGZ4sjvSNg0ClOAhDu%2BQFlLOWMJk7L9Aj0f1XfyLvtyQfP6CJOEtNEENwCptAvWG6KQX2CyDbASTMDiBwy9YklIMKSCEGbAGGnWhH6xjG9ELmntvzEprXqAZ5ZEyPo%2BStJlDGd%2FfcAPsrtiT4OhZQ4SyGdep8p3cO2HPu448g0FWX3cybdImlas4jc7Yf3w4SP6i%2FrhQtGtuVBLpTxEwXYNcc1nCLigh%2BEpWpC2YPemJNHtdhNEwEsULcOkuko2v8B%2FtjDJwCvAbKSQUvTv8hJfoiJzUDX7%2BC4pGn1LYxAmYJH6UZj0F8kTrd7959lXItzfo3mSV1bIiWbvLulFLtRSjUtkX1U5C1duBp4yFJ%2FOHohew8pi82atXYqNS5nGEKRZOX9EGPhiuIhij8lBkoJ0m5De2CCl8MPlRWUteLGtX5MBrslNiHpym1VljlRwGUfbEAtOCpIflWVSda9fnNPPUqXbOMSloa79r49L8kP0vGEavFYWl4mUpnNJlVRlu7jsa5g%2FqvbpGMZUF5gDULHEIXlaIudvEqaKQkZEnTxOllQiFEcLhMJvkKKKKowzcQ4gyDqVDKkEhH8MwBLfAmG0BoiPkj3avaJ808AVmIB0scraYBsuUGssoxgNurF0xQSeykukgKwEbHWJpijIU1oeebIsn93T%2FzH7%2FAmjyna9BnG1hL9Z5EwBwNAYOsla4CsHsqoaRnNWO2yFYD2ZtC8mpl1LVBfRehPAFHr7SmopY91HQYA0AGMUYqwywuoX6p2BJE6Ma313I%2FISsi8ojA0Ri97SJ5Fq3q9BUxxuFqvg8FAy05dRv3XKHzsDzFvItErz4HE2imv%2FyQUQXWCQyTFmKkCKCDmJWtvKGomLM60wF5Ex%2FugvZYMx3GIDdpdoSMzR3KK9Gwy%2FP316%2Bm6Ff643D%2FGfD9%2Bmr5fmyMlt5dwGpsY%2BmDMr3Sgaw9Q%2BzmxNEoIJGz92NpQiUSeYwrGHwEThiBLT9yhrehng8aB3RxJd4xpnGdwDD48yUJBFHh2XggyCFL5wBdP63sFoDdNM0Vecl8Ad0go%2F71wKljmggYC6LJZ54p1Vj77QVmCXnJ1faferzCDeFfCe9gJ6%2FCsSl7s5QQP52a4lV%2Bk6oK2UDYKgR6%2BeV34KZxuwwBGfY4CbG8QL6tZxcIMR6475UnAibBFOoyCK0XWAG%2BnSA%2FGPd0hObqY309vbTNZs8xEZAsZFnoM6xdgeYlDOUiyyH5ziERkg6vjkRxX%2FFqz9ADutvsZwvkXKjdvz4wxFfYCxB0KsWFexj02QaYIE6hK1mf9IE9MHNt1cQriGfADBFmo6RaMTblEneNmv0iRBJbqObNyRDVV9MC5oujmwSRjLxRhQbyL1kdoHBYKCJ2MHyUVvRhlC5JnUAgmVNP2m4qPGgeZ9ogGIYfsA0XXivhgwtAoYYDMdp7mM2fUrw4jRITGAOR4tN8Djs3nMhntVPshmnshC1qW%2ByEJMhVuyFIioI6MWDCUrsMGhi1dk33gwtnGphPY%2BzFmknWvn8zYN8IQFTUylQE19KuX4LVRBjWe5eDEUa8O3vcutQpRy2CyTIQ1wjtoHzk7sTo7A4%2BIozHZHIgIbIgJbQ%2FOgCMzPmBQQsPbkSSGlZvqkiLWqmZRStOVdAR3knhXkivLEYLCBILEkWgnKIbZcdDQgO%2B5A9mcQtIYgaxpuEWUdCWVNV0BZh%2FXqYVC2dHKX912yCd5S1GNpOsQ7K8Tbo3OrcYmsVetw6dzFobG3vehsd0QX3Egc%2BznOQcd%2BzGopgRvF7c61tjdK8K2pUX%2BzffXvumdfrXUGBa3NBxi549wS9XZgHVRv8%2FFwyfKzMoVm6TqFbkOh%2BdbUKLTVKfT5KLRb9IKb5lhQaMswTImID%2BoGZ%2B4Q%2FHxCj%2Bcr29GNSzIKw3aySdcic8sgiBdFt1iz4HYpW7dJI6IAUie2CEOBLJBO1OdLNfJJJDaXoMaaxTZ%2Byud5kxTE6RXeJ4ECwgiPPCcw9FjIHC%2BCIEG0%2F4caaVVLH6dAsixl3THJB8AlWjPCv6Nrkq8F8O%2FouhW5bvIY8MVP%2F4PiGn3XFH4sevNv%2BpD4%2BzUWaoNdvLKLEEkvycMZiL%2Fs7t981F0u2RXLRuhEvlpyRbjiHLmAKpTVSzSzsUpFuQZA20WAhl5hQ05txI628QJWxnQL2N6pQyvqsJcCFCSySuR3C1TwFV5MfxX6a4BFMu89noetXMJRpy5htQQN1fwVwwAV8CQKJCWrS6Nv2sZA4KvLivEnzf0%2B8jOyYVGix8cEpjyfIWkDr1yMDU6RKLJg3GtJk8d0z91tWXzblCabDSEB%2BkKqsGPXvEneSLhl%2BwbK%2BI1SWk5xzMHTMdyhVZrTZ6TeQ1FxbbcJlVR2uoYgBscmiGFHEKeXpkNCveDkrQn1Rt9wHEvATPskQC9Onlj2sBropfi2aTWLP2qW%2F4AuWqob3zGPxTtVO8m4CU3lbrK63MTPjXf8dFREGQ4ERBHgpG%2BbGn56s3BoOEyxgaHjsF9e4g5qrvALKOqbK4ZBCeC4tDUwRaeejrbk%2BDraKsTX0JYcX0dbcvzj0ZZ%2B23FdcqLLZDteOrgrxKnwwDWxmmr2vYZ7FBuFOu75xaVKzzy1eYZfDd3ALeaMRbeYVbHIqwXaESaC2sLe1uaGxMMc6Jr3cJ6Qpe8l8z0k2POf5KA3V0dxmER1JVCwUI%2BajEO2NnaEc3hoUEwjsXFqr6YnXjWdxSAlh5tmU1GOI1eEL04uoIoJ9aeh1GFCxY64tzBhJ8TtCnFBWuqJbRNBFXlxL2YbjqUFCvZp%2FICONIFjDsotkmJy09BsNiTjPJqsyqFn2mbfEDcvD8diXmSUUcirVa5WnllURlSZKZTTFFse2BHVWY1hq%2FigvLc1FKDY23dYY2jUkcWpBak9Y2hcssZNSRmlfHBkK6bsbLUycCRw2M23n9a77EgzpG6j%2BfbKPtdApGJn3kEhclw8pqmTpqNL07nNt2dzFWNxsvjyFCPtfOP40V3%2FivMqy%2BYiuTMra8J6N1V9MmV0xQGLoIl9S7f34Q1SUQn8lqHY%2BtgB%2Fy8va%2Bc2SY3IypWW1J7Ew%2BKwzSpHx%2F3W%2FPzVpw2zk3caTUckm%2BxU0f3rVDzgeFcgyVwzySDxWOe8OTCuVHHRHsdZ1yEixSbcjoh%2BGoE5qCXRxAEjecbfRh%2BtInytY9hrAiDbC9sB4IEHVvz%2BJrz6zxA%2BvXrzVeIATJVJ02lWuVqVxWnwvL5cahDc6hD8F5T4PWVcI9UiXxS54U0Oe6sBX%2BQGiOVIhzGfZIbXcUUryKVnRp%2BhATIo2xNf%2FvKPwnb44hmz0ttAGu6LJ7zY2Qmn9T9Yzpj%2F2PUgRFjToc6k8WoksVpuVXE6F1ylWPfyc8dK32tTh0GPvS1%2BbHUMenBlcPcTf1cj8Adl0CYWFzd3Y45EK8yV1gSdhkNtxzlXDi09V6bGe6rqkKnqxVUNKbVqCsnsaPWISDJyeLzA6iZAho6%2FaomUksiUUlSDzo69ib8zCM9BCA9JTPtugBwNHIESGmzjfxHyLDnv5e2sJS8wPuOZp1LDT%2FECw%2BK58yXvMmyRlayOlY7oIZIBoeFxY0qZUa5s4IWlBvkce%2Fd9Rz7nIGtnuLBh4NoSd7h7kk%2BbO0kkQjwe3Sjf1VoG85VnrdS3PjyQrISLe5Dig3wzAcBuF3xy68s1fs1Fp6xtKevYFZV11IwYSsVEg%2Fst7%2Fd78873TvbOUvZa3Cy%2Fn01iDob1jZCDmR3mwBbtDu3ZYnIC7eFihQS608XkBNrjxeQEZ2w7lTr8xLeJH%2F10AHlFYM23mbdygkDJYdb1zbgOYo%2B0Ac8eCT9jDnNrH%2F4rnVrg5BN7wnkBzc4csAs14ctrNOwQ9dCoqwc1BiZH34WqOfO605pjac2eetJEMVoczuxxJLbRN1z2Wk02jqh4l7maxi%2FF9TcHcLGOGh2XLb8YdHy2g4pSh6ywI3SBl2z32IrtaU9YoK1423Oy3xKcSpO94%2FQzQydptd%2BIxyBpRYL2BT17iRsvaDVI9Nj7lDvr%2FqcU0xNZ93uc%2FlBi0rps6Uxds1xOoDXLCwl0ZrmcQGuWywl%2BRrM8O43zPgqC5AyO8NMYI3Sy7JA2eedyPzNg%2FC1scl4JdRZ5Un%2Bm4Ohn5HYG%2BZmozG9gkJuuI87wnuINVbIJbdptjwCwDy6KUj6HGGxWHyMPjwVu%2Fg8%3D%3C%2Fdiagram%3E%3C%2Fmxfile%3E)
