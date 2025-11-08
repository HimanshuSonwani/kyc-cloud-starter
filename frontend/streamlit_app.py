# streamlit_app.py
# UI for KYC Cloud Starter (uses your deployed FastAPI)
import os
import io
import time
import json
import datetime as dt
from typing import Dict, Tuple

import requests
import streamlit as st


# ------------- Configuration -------------
# Prefer Streamlit secrets, then env var, then text input in the UI.
DEFAULT_API_URL = (
    st.secrets.get("API_URL") if "API_URL" in st.secrets else os.getenv("API_URL", "").strip()
)

POLL_MAX_SECONDS = int(os.getenv("POLL_MAX_SECONDS", "60"))
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "2.0"))


# ------------- Helper functions -------------
def _content_type_from_name(name: str) -> str:
    name = (name or "").lower()
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith(".jpeg") or name.endswith(".jpg"):
        return "image/jpeg"
    # default
    return "image/jpeg"


def _put_binary(url: str, data: bytes, content_type: str) -> Tuple[bool, str]:
    try:
        r = requests.put(url, data=data, headers={"Content-Type": content_type}, timeout=30)
        if 200 <= r.status_code < 300:
            return True, "ok"
        return False, f"PUT {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"PUT error: {e}"


def _post_json(base: str, path: str, payload: dict) -> Tuple[bool, dict | str]:
    try:
        r = requests.post(f"{base.rstrip('/')}{path}", json=payload, timeout=30)
        if 200 <= r.status_code < 300:
            return True, r.json()
        return False, f"POST {r.status_code}: {r.text[:400]}"
    except Exception as e:
        return False, f"POST error: {e}"


def _get_json(base: str, path: str) -> Tuple[bool, dict | str]:
    try:
        r = requests.get(f"{base.rstrip('/')}{path}", timeout=30)
        if 200 <= r.status_code < 300:
            return True, r.json()
        return False, f"GET {r.status_code}: {r.text[:400]}"
    except Exception as e:
        return False, f"GET error: {e}"


# ------------- UI -------------
st.set_page_config(page_title="KYC Cloud UI", page_icon="🪪", layout="centered")
st.title("🪪 KYC Cloud UI")

with st.expander("API connection", expanded=not bool(DEFAULT_API_URL)):
    api_url = st.text_input(
        "API base URL (your FastAPI on Railway, e.g. https://kyc-cloud-starter-production.up.railway.app)",
        value=DEFAULT_API_URL,
        placeholder="https://<your-api>.up.railway.app",
    )
else:
    api_url = DEFAULT_API_URL

col_h, col_ping = st.columns([1, 1])
with col_h:
    if st.button("Check /health", use_container_width=True):
        ok, res = _get_json(api_url, "/health")
        if ok:
            st.success(res)
        else:
            st.error(res)

with col_ping:
    st.caption("Make sure the API URL is reachable and returns `{'ok': True}`")

st.divider()

st.subheader("Submit a document for verification")

doc_type = st.selectbox(
    "Document type",
    ["passport", "driver_license", "aadhaar_offline"],
    index=0,
)

col1, col2 = st.columns(2)
with col1:
    full_name = st.text_input("Full name", value="")
with col2:
    dob = st.date_input("Date of birth", value=dt.date(1999, 1, 1), format="YYYY-MM-DD")

st.caption("Upload images (JPEG/PNG/WEBP). Max a few MB each, depends on your storage config.")

up_front = st.file_uploader("Front image", type=["jpg", "jpeg", "png", "webp"], key="front")
up_back = st.file_uploader("Back image (if applicable)", type=["jpg", "jpeg", "png", "webp"], key="back")
up_selfie = st.file_uploader("Selfie / Face image", type=["jpg", "jpeg", "png", "webp"], key="selfie")

go = st.button("Start verification", type="primary", use_container_width=True)

if go:
    if not api_url:
        st.error("Enter your API base URL first.")
        st.stop()

    if not up_front or not up_selfie:
        st.error("Please upload at least Front and Selfie images.")
        st.stop()

    user_fields = {
        "name": full_name.strip(),
        "dob": str(dob),
    }

    with st.status("Requesting signed URLs…", expanded=False) as status:
        ok, presign = _post_json(
            api_url,
            "/v1/presign",
            {"document_type": doc_type, "user_fields": user_fields},
        )
        if not ok:
            status.update(label="Failed to get signed URLs", state="error")
            st.error(presign)
            st.stop()

        # Expected shape:
        # { "object_keys": {"front": "...", "back": "...", "selfie": "..."}, "upload_urls": {"front": "...", ...} }
        object_keys: Dict[str, str] = presign.get("object_keys", {})
        urls: Dict[str, str] = presign.get("upload_urls", {})
        required_parts = ["front", "selfie"]
        for part in required_parts:
            if not urls.get(part):
                status.update(label=f"Presign missing '{part}' URL", state="error")
                st.stop()

        status.update(label="Uploading images to storage…", state="running")

        # Upload front
        front_ct = _content_type_from_name(up_front.name)
        ok_front, msg_front = _put_binary(urls["front"], up_front.getvalue(), front_ct)
        if not ok_front:
            status.update(label="Upload error (front)", state="error")
            st.error(msg_front)
            st.stop()

        # Upload back (optional)
        if up_back and urls.get("back"):
            back_ct = _content_type_from_name(up_back.name)
            ok_back, msg_back = _put_binary(urls["back"], up_back.getvalue(), back_ct)
            if not ok_back:
                status.update(label="Upload error (back)", state="error")
                st.error(msg_back)
                st.stop()

        # Upload selfie
        selfie_ct = _content_type_from_name(up_selfie.name)
        ok_selfie, msg_selfie = _put_binary(urls["selfie"], up_selfie.getvalue(), selfie_ct)
        if not ok_selfie:
            status.update(label="Upload error (selfie)", state="error")
            st.error(msg_selfie)
            st.stop()

        status.update(label="Creating verification job…", state="running")

        ok, created = _post_json(
            api_url,
            "/v1/verifications",
            {
                "document_type": doc_type,
                "object_keys": object_keys,
                "user_fields": user_fields,
            },
        )
        if not ok:
            status.update(label="Failed to create verification", state="error")
            st.error(created)
            st.stop()

        job_id = created.get("id")
        st.info(f"Verification started, job: `{job_id}`")

        status.update(label="Processing… polling for result", state="running")
        t0 = time.time()
        result = None
        while time.time() - t0 < POLL_MAX_SECONDS:
            ok, data = _get_json(api_url, f"/v1/verifications/{job_id}")
            if not ok:
                # non-fatal transient errors
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            status_txt = data.get("status", "unknown")
            st.write(f"Status: **{status_txt}**")
            if status_txt in {"approved", "review", "rejected"}:
                result = data
                break
            time.sleep(POLL_INTERVAL_SECONDS)

        if not result:
            status.update(label="Timed out waiting for result", state="error")
            st.error("No final status within the polling window.")
            st.stop()

        status.update(label="Completed", state="complete")

    st.success(f"Final status: **{result.get('status')}**")
    cols = st.columns(3)
    with cols[0]:
        st.metric("Score", result.get("score"))
    with cols[1]:
        st.write("Document:", doc_type)
    with cols[2]:
        st.write("Job ID:", result.get("id"))

    st.subheader("Explanations")
    st.json(result.get("explanations", []))

    st.subheader("Parsed fields")
    st.json(result.get("fields", {}))

    st.caption("Raw response")
    st.code(json.dumps(result, indent=2), language="json")


# ------------- Footer -------------
st.divider()
st.caption(
    "Tip: set API_URL in Streamlit Secrets or env. "
    "Procfile should run: `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`"
)
