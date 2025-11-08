import os, time, requests, io
import streamlit as st

# >>>> set this in env on deploy (Railway/Streamlit Cloud)
API_BASE = os.getenv("API_BASE", "https://kyc-cloud-starter-production.up.railway.app")

st.set_page_config(page_title="KYC Demo", page_icon="🪪", layout="centered")
st.title("KYC Uploader 🪪")

with st.sidebar:
    st.markdown("**Backend**")
    st.code(API_BASE)
    st.caption("Change via env var: API_BASE")

st.subheader("Your details")
col1, col2 = st.columns(2)
name = col1.text_input("Full name", "")
dob  = col2.text_input("Date of birth (YYYY-MM-DD)", "")

doc_type = st.selectbox(
    "Document type",
    ["passport", "driver_license", "aadhaar_offline"]
)

st.subheader("Upload images")
front = st.file_uploader("Front", type=["jpg", "jpeg", "png"], key="front")
back  = st.file_uploader("Back",  type=["jpg", "jpeg", "png"], key="back")
selfie= st.file_uploader("Selfie",type=["jpg", "jpeg", "png"], key="selfie")

def _bytes_and_type(sf):
    if not sf:
        return None, None
    b = sf.read()
    # default content-type; R2 pre-sign expects image/jpeg (that’s what your API used)
    ctype = sf.type if sf.type else "image/jpeg"
    # normalize png to jpeg if needed; easiest is to enforce jpeg before upload
    if "png" in ctype:
        st.warning("PNG uploaded; presign expects JPEG. Convert to JPEG if upload fails.")
    return b, ctype

def _upload_signed(url, data_bytes, content_type):
    r = requests.put(url, data=data_bytes, headers={"Content-Type": content_type}, timeout=30)
    r.raise_for_status()

def _post_json(path, payload):
    r = requests.post(f"{API_BASE}{path}", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def _get_json(path):
    r = requests.get(f"{API_BASE}{path}", timeout=30)
    r.raise_for_status()
    return r.json()

go = st.button("Start verification", type="primary", use_container_width=True)

if go:
    if not (name and dob and front and back and selfie):
        st.error("Please fill name & DOB and upload all three images.")
        st.stop()

    with st.status("Presigning & uploading…", expanded=True) as status:
        # 1) presign
        presign_payload = {
            "document_type": doc_type,
            "user_fields": {"name": name, "dob": dob}
        }
        st.write("Requesting presigned URLs…")
        presign = _post_json("/v1/presign", presign_payload)

        upload_urls = presign["upload_urls"]
        object_keys = presign["object_keys"]

        # 2) upload 3 parts to R2/S3
        for label, sf in [("front", front), ("back", back), ("selfie", selfie)]:
            data_bytes, ctype = _bytes_and_type(sf)
            st.write(f"Uploading **{label}** …")
            _upload_signed(upload_urls[label], data_bytes, ctype or "image/jpeg")

        status.update(label="Creating verification job…")

        # 3) create verification job
        create_payload = {
            "document_type": doc_type,
            "object_keys": object_keys,
            "user_fields": {"name": name, "dob": dob}
        }
        create = _post_json("/v1/verifications", create_payload)
        job_id = create["id"]
        st.write(f"Job id: `{job_id}`")

        # 4) poll result
        status.update(label="Processing… (polling up to ~60s)")
        t0 = time.time()
        result = None
        while True:
            resp = _get_json(f"/v1/verifications/{job_id}")
            st.write(resp)
            if resp["status"] not in ("pending", "processing"):
                result = resp
                break
            if time.time() - t0 > 60:
                result = resp
                break
            time.sleep(2)

        status.update(label="Done", state="complete", expanded=False)

    # 5) show outcome
    st.subheader("Result")
    st.json(result)
    st.success(f"Status: **{result['status']}**")
