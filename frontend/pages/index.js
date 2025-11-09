// frontend/pages/index.js
import { useState } from 'react';

export default function Home() {
  const [msg, setMsg] = useState('—');

  const ping = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`);
      const data = await res.json();
      setMsg(JSON.stringify(data));
    } catch (e) {
      setMsg('ERR: ' + (e?.message || 'Failed to fetch'));
    }
  };

  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>KYC Frontend — Step 1</h1>
      <p>Verify connectivity to backend first.</p>
      <button onClick={ping}>Ping /health</button>
      <p>{msg}</p>
    </main>
  );
}
