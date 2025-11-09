"use client";
export const dynamic = "force-dynamic";

import { useState } from "react";

export default function Home() {
  const [docFile, setDocFile] = useState<File | null>(null);
  const [selfieFile, setSelfieFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL;

  const submit = async () => {
    if (!docFile || !selfieFile) return alert("Upload both images");

    setLoading(true);

    const form = new FormData();
    form.append("document", docFile);
    form.append("selfie", selfieFile);

    const res = await fetch(`${API_URL}/v1/verify-kyc`, { method: "POST", body: form });
    const data = await res.json();
    setResult(data);
    setLoading(false);
  };

  return (
    <div style={{ width: 320, margin: "60px auto", textAlign: "center", fontFamily: "sans-serif" }}>
      <h2>KYC Verification</h2>
      <p>Upload ID document and selfie.</p>

      <input type="file" accept="image/*" onChange={(e) => setDocFile(e.target.files?.[0] ?? null)} />
      <br /><br />

      <input type="file" accept="image/*" onChange={(e) => setSelfieFile(e.target.files?.[0] ?? null)} />
      <br /><br />

      <button onClick={submit} disabled={loading} style={{ padding: 8, width: "100%" }}>
        {loading ? "Processing..." : "Verify"}
      </button>

      {result && (
        <div style={{ marginTop: 20 }}>
          <h3>{result.status}</h3>
          <p>{result.reason}</p>
        </div>
      )}
    </div>
  );
}
