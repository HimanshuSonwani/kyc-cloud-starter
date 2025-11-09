import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE; // e.g. https://kyc-cloud-starter-production.up.railway.app

export default function Home() {
  const [front, setFront] = useState(null);
  const [back, setBack] = useState(null);
  const [selfie, setSelfie] = useState(null);
  const [log, setLog] = useState("");
  const [job, setJob] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const append = (m) => setLog((p) => p + m + "\n");

  async function ping() {
    const r = await fetch(`${API}/health`);
    append(await r.text());
  }

  async function run() {
    setBusy(true);
    setLog(""); setResult(null);

    // 1) presign
    append("Presigning…");
    const pres = await fetch(`${API}/v1/presign`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ document_type: "aadhaar_offline", user_fields: {} })
    }).then(r=>r.json());

    // 2) put uploads to R2
    async function put(url, file) {
      await fetch(url, { method:"PUT", headers:{ "Content-Type":"image/jpeg" }, body:file });
    }
    append("Uploading to R2…");
    await Promise.all([
      put(pres.upload_urls.front, front),
      put(pres.upload_urls.back, back),
      put(pres.upload_urls.selfie, selfie),
    ]);

    // 3) create verification
    append("Creating verification job…");
    const created = await fetch(`${API}/v1/verifications`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        document_type: "aadhaar_offline",
        object_keys: pres.object_keys,
        user_fields: {}
      })
    }).then(r=>r.json());
    setJob(created.id);

    // 4) poll
    append(`Job ${created.id} queued. Polling…`);
    let tries = 0;
    while (tries < 120) {
      const data = await fetch(`${API}/v1/verifications/${created.id}`).then(r=>r.json());
      if (["approved","review","error"].includes(data.status)) {
        setResult(data);
        append(`Done: ${JSON.stringify(data)}`);
        setBusy(false);
        return;
      }
      await new Promise(res => setTimeout(res, 2000));
      tries++;
    }
    append("Timed out.");
    setBusy(false);
  }

  return (
    <div style={{maxWidth:720,margin:"48px auto",fontFamily:"Inter,system-ui,Arial"}}>
      <h1>KYC — Demo</h1>

      <button onClick={ping} disabled={busy}>Ping /health</button>

      <h2 style={{marginTop:24}}>Step 1 — Upload</h2>
      <div style={{display:"grid",gap:8}}>
        <label>Front: <input type="file" accept="image/*" onChange={e=>setFront(e.target.files[0])} /></label>
        <label>Back: <input type="file" accept="image/*" onChange={e=>setBack(e.target.files[0])} /></label>
        <label>Selfie: <input type="file" accept="image/*" onChange={e=>setSelfie(e.target.files[0])} /></label>
      </div>
      <button style={{marginTop:12}} disabled={busy || !front || !back || !selfie} onClick={run}>Upload & Verify</button>

      <h2 style={{marginTop:24}}>Logs</h2>
      <pre style={{background:"#0b1022",color:"#d4e1ff",padding:16,whiteSpace:"pre-wrap"}}>{log || "…"}</pre>

      {result && (
        <>
          <h2>Result</h2>
          <pre style={{background:"#f7f7f7",padding:16}}>{JSON.stringify(result, null, 2)}</pre>
          {result.fields && (
            <div style={{marginTop:8}}>
              <strong>Extracted:</strong> {result.fields.full_name || "?"} | {result.fields.dob || "?"} | {result.fields.document_number || "?"}
            </div>
          )}
        </>
      )}
    </div>
  );
}
