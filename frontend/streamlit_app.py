import os
import time
import requests
import streamlit as st
from typing import Dict

# ----------------------------
# Config
# ----------------------------
API_BASE_DEFAULT = os.getenv("API_BASE_URL", "").strip()  # e.g., https://your-api.up.railway.app

# ----------------------------
# API helpers (modular)
# ----------------------------
def api_health(api_base: str) -> bool:
    try:
        r = requests.get(f"{api_base}/health", timeout=10)
        r.raise_for_status()
        data = r.json()
        return bool(data.get("ok"))
    except Exception:
        return False

def api_presign(api_base: str, document_type: str, user_fields: Dict) -> Dict:
    r = requests.post(
        f"{api_base}/v1/presign",
        json={"document_type": document_type, "user_fields": user_fields},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def upload_to_presigned(put_url: str, content: bytes, content_type: str) -> None:
    resp = requests.put(put_url, data=content, headers={"Content-Type": content_type}, timeout=60)
    resp.raise_for_status()

def api_create_verification(api_base: str, document_type: str, object_keys: Dict, user_fields: Dict) -> str:
    r = requests.post(
        f"{api_base}/v1/verifications",
        json={"document_type": document_type, "object_keys": object_keys, "user_fields": user_fields},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["id"]

def api_get_status(api_base: str, job_id: str) -> Dict:
    r = requests.get(f"{api_base}/v1/verifications/{job_id}", timeout=30)
    r.raise_for_status()
    return r.json()

# ----------------------------
# Utils
# ----------------------------
def guess_content_type(filename: str) -> str:
    fn = (filename or "").lower()
    if fn.endswith(".png"):
        return "image/png"
    return "image/jpeg"

# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="KYC Cloud UI", page_icon="🪪", layout="centered")
st.title("🪪 KYC Cloud – Simple Frontend")

with st.expander("Backend settings", expanded=True):
    api_base = st.text_input(
        "FASTAPI base URL",
        value=API_BASE_DEFAULT,
        placeholder="https://your-api.up.railway.app",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Check /health"):
            if not api_base:
                st.error("Enter API base URL.")
            else:
                st.success("Healthy ✅") if api_health(api_base) else st.error("Unreachable ❌")
    with col2:
        st.caption("Tip: set API_BASE_URL env var on Railway to prefill this.")

st.markdown("---")

st.subheader("1) User details")
name = st.text_input("Full name", value="Himanshu Sonwani")
dob  = st.text_input("DOB (YYYY-MM-DD)", value="1999-05-20")
doc_type = st.selectbox("Document type", ["passport", "driver_license", "aadhaar_offline"])

st.subheader("2) Upload images")
front  = st.file_uploader("Front/Document image", type=["jpg", "jpeg", "png"])
back   = st.file_uploader("Back image / second page", type=["jpg", "jpeg", "png"])
selfie = st.file_uploader("Selfie", type=["jpg", "jpeg", "png"])

if st.button("Start verification 🚀", type="primary", use_container_width=True):
    if not api_base:
        st.error("Enter API base URL.")
        st.stop()
    if not (front and back and selfie):
        st.error("Upload all three images (front/back/selfie).")
        st.stop()

    user_fields = {"name": name.strip(), "dob": dob.strip()}

    try:
        with st.status("Requesting presigned URLs…", expanded=False) as s:
            presigned = api_presign(api_base, doc_type, user_fields)
            object_keys = presigned["object_keys"]
            upload_urls = presigned["upload_urls"]
            s.update(label="Uploading to storage…", state="running")

        upload_to_presigned(upload_urls["front"],  front.read(),  guess_content_type(front.name))
        upload_to_presigned(upload_urls["back"],   back.read(),   guess_content_type(back.name))
        upload_to_presigned(upload_urls["selfie"], selfie.read(), guess_content_type(selfie.name))

        with st.status("Creating verification job…", expanded=False) as s:
            job_id = api_create_verification(api_base, doc_type, object_keys, user_fields)
            s.update(label=f"Job created: {job_id}", state="complete")
        st.info(f"Job ID: `{job_id}`")

        with st.status("Processing… polling status", expanded=True) as s:
            for attempt in range(30):  # ~60s total at 2s interval
                data = api_get_status(api_base, job_id)
                status = data.get("status", "unknown")
                st.write(f"Attempt {attempt+1}: **{status}**")
                if status in {"approved", "rejected", "review"}:
                    st.success("Done ✅")
                    st.subheader("Result")
                    st.json(data)
                    break
                time.sleep(2)
            else:
                st.warning("Timed out waiting for result. Try again later.")

    except requests.HTTPError as e:
        st.error(f"HTTP error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        st.error(f"Error: {e}")
