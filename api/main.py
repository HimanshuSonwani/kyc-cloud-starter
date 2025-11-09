import os, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import boto3
from botocore.config import Config
import redis

app = FastAPI(title="KYC Cloud API")

# --- CORS ---
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "").strip()
allowed = [FRONTEND_ORIGIN] if FRONTEND_ORIGIN else ["*"]   # fallback for quick testing
# You can also hard-list multiple:
# allowed = [FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],     # OPTIONS handled automatically
    allow_headers=["*"],
)

# ENV vars from Railway
S3_ENDPOINT = os.getenv("S3_ENDPOINT")  # e.g. https://<accountid>.r2.cloudflarestorage.com
S3_REGION = os.getenv("S3_REGION", "auto")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET", "kyc-raw")
REDIS_URL = os.getenv("REDIS_URL")

# Redis
r = redis.from_url(REDIS_URL, decode_responses=True)

# R2 client
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=None,
    config=Config(signature_version="s3v4"),
)

# ======== MODELS ========
class PresignReq(BaseModel):
    document_type: str = Field(..., examples=["passport", "driver_license", "aadhaar_offline"])
    user_fields: dict = Field(default_factory=dict)

class PresignResp(BaseModel):
    object_keys: dict
    upload_urls: dict

class CreateVerReq(BaseModel):
    document_type: str
    object_keys: dict
    user_fields: dict = Field(default_factory=dict)

# ======== ROUTES ========
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/presign", response_model=PresignResp)
def presign(req: PresignReq):
    try:
        uid = str(uuid.uuid4())
        keys = {
            "front": f"raw/{uid}-front.jpg",
            "back": f"raw/{uid}-back.jpg",
            "selfie": f"raw/{uid}-selfie.jpg",
        }

        urls = {}
        for part, key in keys.items():
            urls[part] = s3.generate_presigned_url(
                ClientMethod="put_object",
                Params={"Bucket": S3_BUCKET, "Key": key, "ContentType": "image/jpeg"},
                ExpiresIn=600,
            )

        return {"object_keys": keys, "upload_urls": urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/verifications")
def create_verification(req: CreateVerReq):
    job_id = "ver_" + str(uuid.uuid4())
    r.hset(
        f"ver:{job_id}",
        mapping={
            "status": "pending",
            "score": "",
            "document_type": req.document_type,
            "front": req.object_keys.get("front", ""),
            "back": req.object_keys.get("back", ""),
            "selfie": req.object_keys.get("selfie", ""),
        },
    )
    r.rpush("jobs", job_id)
    return {"id": job_id, "status": "pending"}


@app.get("/v1/verifications/{job_id}")
def get_verification(job_id: str):
    data = r.hgetall(f"ver:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    fields = None
    if "fields" in data:
        try:
            fields = json.loads(data["fields"])
        except Exception:
            fields = None
    out = {
        "id": job_id,
        "status": data.get("status","unknown"),
        "score": int(data["score"]) if data.get("score","").isdigit() else None,
        "explanations": [
            {"check": "selfie_face_present", "pass": data.get("status")=="approved" or data.get("status")=="review"},
            {"check": "id_front_parsed", "pass": fields is not None},
        ],
        "fields": fields,
        "report_pdf_url": None
    }
    return out
