import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE; // no trailing slash

export default function Home() {
  const [front, setFront] = useState(null);
  const [back, setBack] = useState(null);
  const [selfie, setSelfie] = useState(null);
  const [log, setLog] = useState("");

  async function ping() {
    const res = await fetch(`${API}/health`);
    setLog(await res.text());
  }

  async function upload() {
    if (!front || !back || !selfie) {
      setLog("Select all 3 files first.");
      return;
    }

    // 1) ask backend for presigned PUT URLs with the exact MIME types
    const body = {
      document_type: "aadhaar_offline",
      user_fields: {},
      content_types: {
        front: front.type || "image/jpeg",
        back: back.type || "image/jpeg",
        selfie: selfie.type || "image/jpeg",
      },
    };

    const pres = await fetch(`${API}/v1/presign`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!pres.ok) {
      setLog(`presign failed: ${pres.status}`);
      return;
    }
    const { upload_urls, object_keys } = await pres.json();

    // 2) PUT each file to R2 using the SAME Content-Type the server signed
    const put = (url, file) =>
      fetch(url, { method: "PUT", headers: { "Content-Type": file.type || "image/jpeg" }, body: file });

    const r = await Promise.all([
      put(upload_urls.front, front),
      put(upload_urls.back, back),
      put(upload_urls.selfie, selfie),
    ]);

    if (r.some(x => !x.ok)) {
      const codes = await Promise.all(r.map(async x => `${x.status}`));
      setLog("Upload error: " + codes.join(", "));
      return;
    }

    // 3) create the verification job
    const jobRes = await fetch(`${API}/v1/verifications`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        document_type: "aadhaar_offline",
        object_keys,
        user_fields: {},
      }),
    });
    const job = await jobRes.json();

    // 4) show debug list to prove files are in R2
    const list = await fetch(`${API}/debug/list`).then(r => r.json());

    setLog(
      `Uploaded.\nJob: ${JSON.stringify(job)}\nR2 objects (${list.count}):\n${list.keys.join("\n")}`
    );
  }

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h1>KYC Frontend — Step 1</h1>
      <button onClick={ping}>Ping /health</button>
      <pre>{log}</pre>

      <h2>Step 2 — Upload</h2>
      <div>Front: <input type="file" accept="image/*" onChange={e => setFront(e.target.files?.[0] || null)} /></div>
      <div>Back: <input type="file" accept="image/*" onChange={e => setBack(e.target.files?.[0] || null)} /></div>
      <div>Selfie: <input type="file" accept="image/*" onChange={e => setSelfie(e.target.files?.[0] || null)} /></div>
      <button onClick={upload} style={{ marginTop: 12 }}>Upload & Create Job</button>
    </div>
  );
}
