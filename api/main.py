import os, uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import boto3
from botocore.config import Config
import redis
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="KYC Cloud API")

# ------- CORS (allow your front-end origin) -------
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")  # set to https://your-frontend.up.railway.app in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------- ENV -------
S3_ENDPOINT = os.getenv("S3_ENDPOINT")              # e.g. Cloudflare R2: https://<accountid>.r2.cloudflarestorage.com
S3_REGION   = os.getenv("S3_REGION", "auto")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET     = os.getenv("S3_BUCKET", "kyc-raw")
REDIS_URL     = os.getenv("REDIS_URL")

# ------- Clients -------
r = redis.from_url(REDIS_URL, decode_responses=True)

if S3_ENDPOINT:
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=None if S3_REGION == "auto" else S3_REGION,
        config=Config(signature_version="s3v4"),
    )
else:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=os.getenv("S3_REGION", "ap-south-1"),
        config=Config(signature_version="s3v4"),
    )

# ------- Models -------
class PresignReq(BaseModel):
    document_type: str = Field(..., examples=["passport","driver_license","aadhaar_offline"])
    user_fields: dict = Field(default_factory=dict)

class PresignResp(BaseModel):
    object_keys: dict
    upload_urls: dict
    content_types: dict

class CreateVerReq(BaseModel):
    document_type: str
    object_keys: dict
    user_fields: dict = Field(default_factory=dict)

# ------- Helpers -------
def choose_ext_and_type(filename_or_mime: str):
    """
    Accept JPEG/PNG/WEBP from the frontend and return (ext, mime).
    filename_or_mime can be the file MIME (image/png) or a name like foo.png
    """
    s = filename_or_mime.lower()
    if "png" in s:
        return (".png", "image/png")
    if "webp" in s:
        return (".webp", "image/webp")
    # default jpeg
    return (".jpg", "image/jpeg")

# ------- Endpoints -------
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/v1/presign", response_model=PresignResp)
def presign(req: PresignReq):
    """
    Frontend should call this with the selected files' MIME types (or names) so we
    can issue correctly typed PUT URLs. If none are provided we default to jpeg.
    Expect frontend to send e.g. user_fields={"front_type":"image/png", "back_type":"image/jpeg", "selfie_type":"image/png"}
    or file names.
    """
    uid = str(uuid.uuid4())

    # detect each part's extension and mime
    fext, fmime = choose_ext_and_type(req.user_fields.get("front_type", "image/jpeg"))
    bext, bmime = choose_ext_and_type(req.user_fields.get("back_type", "image/jpeg"))
    sext, smime = choose_ext_and_type(req.user_fields.get("selfie_type", "image/jpeg"))

    keys = {
        "front":  f"raw/{uid}-front{fext}",
        "back":   f"raw/{uid}-back{bext}",
        "selfie": f"raw/{uid}-selfie{sext}",
    }
    content_types = {"front": fmime, "back": bmime, "selfie": smime}

    urls = {}
    for part, key in keys.items():
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": key,
            },
            ExpiresIn=600,
        )
        urls[part] = url

    return {"object_keys": keys, "upload_urls": urls, "content_types": content_types}

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
    out = {
        "id": job_id,
        "status": data.get("status", "unknown"),
        "score": int(data["score"]) if data.get("score", "").isdigit() else None,
        "explanations": [
            {"check": "dummy_pipeline", "pass": data.get("status") == "approved", "detail": "Simulated check"},
        ],
        "fields": {"name": "TBD", "dob": "TBD"},
        "report_pdf_url": None,
    }
    return out
