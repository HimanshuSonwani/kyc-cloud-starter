import os, io, time, json
import base64
import boto3
import redis
import cv2
import numpy as np
from PIL import Image
from botocore.config import Config
from openai import OpenAI
from urllib.parse import urlparse

# ---- ENV / clients ----
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_REGION   = os.getenv("S3_REGION", "auto")
S3_ACCESS   = os.getenv("S3_ACCESS_KEY")
S3_SECRET   = os.getenv("S3_SECRET_KEY")
S3_BUCKET   = os.getenv("S3_BUCKET", "kyc-raw")
REDIS_URL   = os.getenv("REDIS_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Redis: force TLS if using rediss:// and disable cert verification when needed
redis_kwargs = dict(decode_responses=True)
if REDIS_URL.startswith("rediss://"):
    redis_kwargs.update({"ssl": True, "ssl_cert_reqs": None})
r = redis.from_url(REDIS_URL, **redis_kwargs)

# S3 / R2 client
if S3_ENDPOINT:
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        region_name=None if S3_REGION == "auto" else S3_REGION,
        config=Config(signature_version="s3v4"),
    )
else:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        region_name=os.getenv("S3_REGION", "ap-south-1"),
        config=Config(signature_version="s3v4"),
    )

client = OpenAI(api_key=OPENAI_API_KEY)

def get_obj_bytes(key: str) -> bytes:
    buf = io.BytesIO()
    s3.download_fileobj(S3_BUCKET, key, buf)
    return buf.getvalue()

def face_present(img_bytes: bytes) -> bool:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(arr, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    return len(faces) >= 1

def ocr_front_with_openai(front_bytes: bytes) -> dict:
    b64 = base64.b64encode(front_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

    SYSTEM = (
        "You read government ID cards. "
        "Return compact JSON: {\"full_name\": string|null, \"dob\": string|null, \"document_number\": string|null}. "
        "If uncertain, use null. Respond ONLY with JSON."
    )
    USER = [
        {"type": "text", "text": "Extract fields from this ID front:"},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    # OpenAI Responses API (vision)
    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": USER},
        ],
    )
    text = resp.output_text.strip()
    try:
        return json.loads(text)
    except Exception:
        return {"full_name": None, "dob": None, "document_number": None}

def score_verification(has_face: bool, fields: dict) -> int:
    score = 0
    if has_face: score += 40
    if fields.get("full_name"): score += 30
    if fields.get("dob"): score += 20
    if fields.get("document_number"): score += 10
    return score

def process_job(job_id: str, doc_type: str, keys: dict):
    try:
        front_b  = get_obj_bytes(keys.get("front", ""))
        selfie_b = get_obj_bytes(keys.get("selfie", ""))

        has_face = face_present(selfie_b)
        fields   = ocr_front_with_openai(front_b)

        score  = score_verification(has_face, fields)
        status = "approved" if score >= 70 else "review"

        r.hset(f"ver:{job_id}", mapping={
            "status": status,
            "score": str(score),
            "fields": json.dumps(fields),
        })
    except Exception as e:
        r.hset(f"ver:{job_id}", mapping={
            "status": "error",
            "score": "",
            "error": str(e),
        })

def main_loop():
    print("Worker started. Waiting for jobs…")
    while True:
        try:
            job_id = r.lpop("jobs")
        except redis.exceptions.ConnectionError:
            # backoff on transient TLS/socket issues
            time.sleep(2.0)
            continue

        if not job_id:
            time.sleep(0.8)
            continue

        data = r.hgetall(f"ver:{job_id}")
        if not data:
            continue

        doc_type = data.get("document_type", "unknown")
        keys = {
            "front":  data.get("front", ""),
            "back":   data.get("back", ""),
            "selfie": data.get("selfie", ""),
        }
        r.hset(f"ver:{job_id}", mapping={"status": "processing"})
        process_job(job_id, doc_type, keys)

if __name__ == "__main__":
    main_loop()
