import { useState } from "react";
import UploadStep from "../components/UploadStep";

export default function Home() {
  const [out, setOut] = useState("");
  const API = process.env.NEXT_PUBLIC_API_BASE;

  async function ping() {
    try {
      const r = await fetch(`${API}/health`);
      setOut(await r.text());
    } catch (e) {
      setOut("ERR: " + e.message);
    }
  }

  return (
    <main style={{padding:24}}>
      <h1>KYC Frontend — Step 1</h1>
      <p>Verify connectivity to backend first.</p>
      <button onClick={ping}>Ping /health</button>
      <pre>{out}</pre>

      <h2 style={{marginTop:24}}>Step 2 — Upload</h2>
      <UploadStep />
    </main>
  );
}
