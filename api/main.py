import os
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from botocore.config import Config
import redis

app = FastAPI(title="KYC Cloud API")

# ---- CORS ----
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "").strip()
allow = [FRONTEND_ORIGIN] if FRONTEND_ORIGIN else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Redis ----
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL is required")
r = redis.from_url(REDIS_URL, decode_responses=True)

# ---- S3 / R2 (optional but recommended) ----
S3_ENDPOINT = os.getenv("S3_ENDPOINT") or None
S3_REGION   = os.getenv("S3_REGION", "auto")
S3_ACCESS   = os.getenv("S3_ACCESS_KEY")
S3_SECRET   = os.getenv("S3_SECRET_KEY")
S3_BUCKET   = os.getenv("S3_BUCKET")

s3_client = None
if S3_ACCESS and S3_SECRET and S3_BUCKET:
    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT or None,
        region_name=S3_REGION if S3_ENDPOINT else None,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        config=Config(s3={"addressing_style": "virtual"} if S3_ENDPOINT else None),
    )

def s3_put_bytes(key: str, data: bytes, content_type: str):
    if not s3_client:
        return None
    s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=data, ContentType=content_type)
    # Public URL (for R2 use the custom/public domain if configured; otherwise return key)
    return key

@app.get("/health")
def health():
    try:
        r.ping()
        ok = True
    except Exception:
        ok = False
    return {"status": "ok", "redis": ok}

@app.post("/jobs/start")
async def start_job(
    front: UploadFile = File(...),
    back: UploadFile  = File(...),
    selfie: UploadFile = File(...),
):
    jid = str(uuid.uuid4())[:8]

    # upload to S3/R2 if configured
    front_key = back_key = selfie_key = None
    try:
        front_key  = f"uploads/{jid}/front_{front.filename}"
        front_bytes = await front.read()
        if s3_client:
            s3_put_bytes(front_key, front_bytes, front.content_type or "application/octet-stream")

        back_key   = f"uploads/{jid}/back_{back.filename}"
        back_bytes = await back.read()
        if s3_client:
            s3_put_bytes(back_key, back_bytes, back.content_type or "application/octet-stream")

        selfie_key = f"uploads/{jid}/selfie_{selfie.filename}"
        selfie_bytes = await selfie.read()
        if s3_client:
            s3_put_bytes(selfie_key, selfie_bytes, selfie.content_type or "application/octet-stream")
    except Exception as e:
        raise HTTPException(500, f"Storage error: {e}")

    # init job record
    r.hset(f"ver:{jid}", mapping={
        "status": "queued",
        "score": "",
        "fields": "",
        "front_key": front_key or "",
        "back_key": back_key or "",
        "selfie_key": selfie_key or "",
    })
    r.rpush("jobs", jid)
    return {"id": jid, "status": "queued"}

class JobResp(BaseModel):
    id: str
    status: str
    score: Optional[int] = None
    fields: Optional[dict] = None
    report_pdf_url: Optional[str] = None

@app.get("/jobs/{job_id}", response_model=JobResp)
def get_job(job_id: str):
    data = r.hgetall(f"ver:{job_id}")
    if not data:
        raise HTTPException(404, "unknown job")

    fields = None
    if data.get("fields"):
        try:
            import json
            fields = json.loads(data["fields"])
        except Exception:
            fields = None

    score = None
    if data.get("score") and data["score"].isdigit():
        score = int(data["score"])

    return {
        "id": job_id,
        "status": data.get("status", "unknown"),
        "score": score,
        "fields": fields,
        "report_pdf_url": None
    }
