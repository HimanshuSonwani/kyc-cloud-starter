# KYC Cloud Starter (Railway/Render)

**Goal:** Deploy fast to the cloud **without** local Docker/MinIO headaches.
Stack: **FastAPI (API)** + **Worker** + **Upstash Redis** + **Cloud storage (R2/S3)**.

---

## What you'll set up (10–20 min)
- **Upstash Redis** (serverless) → copy the `REDIS_URL`
- **Cloud storage** (choose one): 
  - **Cloudflare R2** (cheap, S3-compatible) or 
  - **AWS S3** (any region)
- **Railway** (or **Render**) → deploy `api/` and `worker/` services from this repo

---

## 1) Create Redis (Upstash)
1. Go to https://upstash.com → Redis → **Create database** (Region near you).
2. Copy the **Redis URL** (format: `redis://default:<password>@...:port`).
3. Save as `REDIS_URL`.

## 2) Create Storage (R2 or S3)

### Option A: Cloudflare **R2**
1. Cloudflare Dashboard → **R2** → **Create bucket** (e.g., `kyc-raw`).
2. In **R2 → Settings → S3 API**, note your **Account ID**.
3. Create an **Access Key** (Access Key ID + Secret Access Key).
4. S3 endpoint:
   ```
   https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   ```

### Option B: **AWS S3**
1. Create an S3 bucket (e.g., `kyc-raw`) in a region (e.g., `ap-south-1`).
2. Create an **IAM user** with programmatic access (S3 permissions limited to that bucket).
3. Save Access Key ID + Secret.
4. Endpoint: leave empty; set `S3_REGION` to your region (e.g., `ap-south-1`).

---

## 3) Deploy on **Railway**
1. Push this folder to **GitHub** as a new repo (e.g., `kyc-cloud-starter`).
2. https://railway.app → **New Project** → **Deploy from Repo** → select it.
3. Railway detects two services:
   - `api/` (Dockerfile)
   - `worker/` (Dockerfile)
4. Set **Environment Variables** for **both** services:
   - `REDIS_URL` = (from Upstash)
   - `S3_ENDPOINT` = (R2 endpoint or leave empty for AWS)
   - `S3_REGION` = `auto` for R2; for AWS use your region (e.g., `ap-south-1`)
   - `S3_ACCESS_KEY` = your key
   - `S3_SECRET_KEY` = your secret
   - `S3_BUCKET` = `kyc-raw`
5. **API service only** add:
   - `API_HOST` = `0.0.0.0`
   - `API_PORT` = `8000`
6. Click **Deploy**. After build completes, open the API logs for:
   - `Uvicorn running on 0.0.0.0:8000`
7. Copy the **Public URL** (e.g., `https://api-xxxxx.up.railway.app`).

---

## 4) Use the API
### Health
```
GET https://YOUR_API/health  →  {"ok": true}
```

### Presign
```bash
curl -s -X POST "https://YOUR_API/v1/presign"   -H "Content-Type: application/json"   -d '{
    "document_type":"passport",
    "user_fields":{"name":"Himanshu Sonwani","dob":"1999-05-20"}
  }'
```

### Upload to R2/S3
```bash
curl -X PUT -T ./front.jpg  "<front_signed_url>"
curl -X PUT -T ./back.jpg   "<back_signed_url>"
curl -X PUT -T ./selfie.jpg "<selfie_signed_url>"
```

### Create verification
```bash
curl -s -X POST "https://YOUR_API/v1/verifications"   -H "Content-Type: application/json"   -d '{
    "document_type":"passport",
    "object_keys":{
      "front":"raw/UUID-front.jpg",
      "back":"raw/UUID-back.jpg",
      "selfie":"raw/UUID-selfie.jpg"
    },
    "user_fields":{"name":"Himanshu Sonwani","dob":"1999-05-20"}
  }'
```

### Poll status
```bash
curl -s "https://YOUR_API/v1/verifications/ver_XXXX"
```

You will see `pending → processing → approved/review/rejected` (dummy score).
