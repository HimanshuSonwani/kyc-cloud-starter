import { useState } from 'react';

export default function Home() {
  const [msg, setMsg] = useState('—');

  const ping = async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE;        // <- from .env.local
      const res = await fetch(`${base}/health`, { mode: 'cors' });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const text = await res.text();
      setMsg(`OK: ${text}`);
    } catch (e) {
      setMsg(`ERR: ${e.message}`);
    }
  };

  return (
    <div style={{ padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>KYC Frontend — Step 1</h1>
      <p>Verify connectivity to backend first.</p>
      <button onClick={ping}>Ping /health</button>
      <p>{msg}</p>
    </div>
  );
}
