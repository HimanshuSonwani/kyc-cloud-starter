import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE;

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
    try {
      const r = await fetch(`${API}/health`);
      const j = await r.json();
      append(`API /health: ${JSON.stringify(j)}`);
    } catch (e) {
      append(`API /health error: ${e}`);
    }
  }

  async function startJob() {
    if (!front || !back || !selfie) {
      alert("Upload front, back, and selfie first.");
      return;
    }
    setBusy(true);
    setResult(null);
    setJob(null);
    try {
      const fd = new FormData();
      fd.append("front", front);
      fd.append("back", back);
      fd.append("selfie", selfie);
      const r = await fetch(`${API}/jobs/start`, { method: "POST", body: fd });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const j = await r.json();
      setJob(j.id);
      append(`Started job: ${j.id}`);
    } catch (e) {
      append(`Start job error: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!job) return;
    let st = null;
    async function poll() {
      try {
        const r = await fetch(`${API}/jobs/${job}`);
        const j = await r.json();
        if (j.status) {
          append(`Status ${job}: ${j.status}${j.score != null ? ` (${j.score})` : ""}`);
          if (["approved", "review", "rejected", "error"].includes(j.status)) {
            setResult(j);
            clearInterval(st);
            st = null;
          }
        }
      } catch (e) {
        append(`Poll error: ${e}`);
      }
    }
    st = setInterval(poll, 1500);
    return () => st && clearInterval(st);
  }, [job]);

  return (
    <div style={{ maxWidth: 720, margin: "40px auto", fontFamily: "Inter, system-ui, Arial" }}>
      <h1>KYC Demo</h1>

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "1fr", marginTop: 12 }}>
        <label>
          ID front:
          <input type="file" accept="image/*" onChange={(e) => setFront(e.target.files?.[0] || null)} />
        </label>
        <label>
          ID back:
          <input type="file" accept="image/*" onChange={(e) => setBack(e.target.files?.[0] || null)} />
        </label>
        <label>
          Selfie:
          <input type="file" accept="image/*" onChange={(e) => setSelfie(e.target.files?.[0] || null)} />
        </label>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={ping} disabled={busy}>Ping API</button>
          <button style={{ marginTop: 12 }} disabled={busy || !front || !back || !selfie} onClick={startJob}>
            Start Verification
          </button>
        </div>
      </div>

      <h2 style={{ marginTop: 24 }}>Log</h2>
      <pre style={{ background: "#111", color: "#0f0", padding: 16, minHeight: 140, whiteSpace: "pre-wrap" }}>{log}</pre>

      {result && (
        <>
          <h2>Result</h2>
          <pre style={{ background: "#f7f7f7", padding: 16 }}>{JSON.stringify(result, null, 2)}</pre>
          {result.fields && (
            <div style={{ marginTop: 8 }}>
              <strong>Extracted:</strong>{" "}
              {result.fields.full_name || "?"} | {result.fields.dob || "?"} | {result.fields.document_number || "?"}
            </div>
          )}
        </>
      )}
    </div>
  );
}
