import os, io, time, json, uuid
import boto3
import redis
import cv2
from PIL import Image
from botocore.config import Config
from openai import OpenAI

# ---- ENV / clients ----
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_REGION   = os.getenv("S3_REGION", "auto")
S3_ACCESS   = os.getenv("S3_ACCESS_KEY")
S3_SECRET   = os.getenv("S3_SECRET_KEY")
S3_BUCKET   = os.getenv("S3_BUCKET", "kyc-raw")
REDIS_URL   = os.getenv("REDIS_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

r = redis.from_url(REDIS_URL, decode_responses=True)

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

# simple helper: download object to bytes
def get_obj_bytes(key: str) -> bytes:
    buf = io.BytesIO()
    s3.download_fileobj(S3_BUCKET, key, buf)
    return buf.getvalue()

# basic face presence check with OpenCV haarcascade
def face_present(img_bytes: bytes) -> bool:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # lightweight bundled cascade
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(arr, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    return len(faces) >= 1

# call OpenAI Vision to extract structured fields from the front image
def ocr_front_with_openai(front_bytes: bytes) -> dict:
    # convert to data URL to send as inline image (keeps things simple)
    import base64
    b64 = base64.b64encode(front_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

    SYSTEM = (
        "You are reading government ID cards. "
        "Extract a compact JSON with fields: {full_name, dob, document_number}."
        "If uncertain, use null. Respond ONLY with JSON."
    )
    USER = [
        {"type": "text", "text": "Extract JSON fields from this ID front."},
        {"type": "image_url", "image_url": {"url": data_url}}
    ]

    # Responses API with image inputs (Vision)
    resp = client.responses.create(
        model="gpt-4o-mini",             # inexpensive multimodal
        input=[{"role":"system","content":SYSTEM},
               {"role":"user","content":USER}]
    )
    text = resp.output_text  # the assistant's text

    try:
        # the model already returns JSON when prompted properly
        data = json.loads(text)
    except Exception:
        data = {"full_name": None, "dob": None, "document_number": None}
    return data

# scoring heuristic
def score_verification(has_face: bool, fields: dict) -> int:
    score = 0
    if has_face: score += 40
    if fields.get("full_name"): score += 30
    if fields.get("dob"): score += 20
    if fields.get("document_number"): score += 10
    return score

def process_job(job_id: str, doc_type: str, keys: dict):
    try:
        front_b = get_obj_bytes(keys.get("front",""))
        selfie_b = get_obj_bytes(keys.get("selfie",""))

        # 1) selfie has a face?
        import numpy as np
        has_face = face_present(selfie_b)

        # 2) read ID front via OpenAI (OCR-ish)
        fields = ocr_front_with_openai(front_b)

        # 3) compute score / decision
        score = score_verification(has_face, fields)
        status = "approved" if score >= 70 else "review"

        # 4) persist
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
        job_id = r.lpop("jobs")
        if not job_id:
            time.sleep(1.0)
            continue
        data = r.hgetall(f"ver:{job_id}")
        if not data:
            continue
        doc_type = data.get("document_type","unknown")
        keys = {
            "front":  data.get("front",""),
            "back":   data.get("back",""),
            "selfie": data.get("selfie",""),
        }
        r.hset(f"ver:{job_id}", mapping={"status":"processing"})
        process_job(job_id, doc_type, keys)

if __name__ == "__main__":
    main_loop()
