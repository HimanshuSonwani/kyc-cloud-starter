'use client';
import {useState} from 'react';

export default function KycForm() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');

  const onSelect = (e) => setFile(e.target.files?.[0] || null);
  const submit = async (e) => {
    e.preventDefault();
    if (!file) return setStatus('Pick a file first');
    try {
      setStatus('Uploading…');
      const form = new FormData();
      form.append('file', file);
      // REPLACE with your backend URL:
      const res = await fetch('https://<YOUR-BACKEND>/upload', { method: 'POST', body: form });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStatus('Uploaded ✅');
    } catch (err) {
      setStatus(`Failed: ${String(err.message || err)}`);
    }
  };

  return (
    <form onSubmit={submit} style={{display:'grid', gap:12}}>
      <input type="file" onChange={onSelect} accept="image/*,application/pdf" />
      <button type="submit">Upload</button>
      <div>{status}</div>
    </form>
  );
}
