// frontend/components/KycForm.jsx
'use client';

import { useState } from 'react';

export default function KycForm() {
  const [docFile, setDocFile] = useState(null);
  const [selfieFile, setSelfieFile] = useState(null);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.API_BASE_URL;

  const onDocChange = (e) => setDocFile(e.target.files?.[0] || null);
  const onSelfieChange = (e) => setSelfieFile(e.target.files?.[0] || null);

  const submit = async () => {
    if (!docFile || !selfieFile) {
      setStatus('Please select both a document photo and a selfie.');
      return;
    }
    try {
      setLoading(true);
      setStatus('Uploading…');

      // 1) presign for document
      const presignDoc = await fetch(`${apiBase}/v1/presign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: docFile.name, content_type: docFile.type }),
      }).then(r => r.json());

      // 2) presign for selfie
      const presignSelfie = await fetch(`${apiBase}/v1/presign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: selfieFile.name, content_type: selfieFile.type }),
      }).then(r => r.json());

      // 3) upload to R2/S3
      await fetch(presignDoc.url, { method: 'PUT', headers: { 'Content-Type': docFile.type }, body: docFile });
      await fetch(presignSelfie.url, { method: 'PUT', headers: { 'Content-Type': selfieFile.type }, body: selfieFile });

      // 4) trigger verification
      const verify = await fetch(`${apiBase}/v1/verifications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_url: presignDoc.public_url,
          selfie_url: presignSelfie.public_url,
        }),
      }).then(r => r.json());

      setStatus(`Submitted. Job ID: ${verify.job_id}. Checking result…`);

      // 5) poll result (simple demo)
      let tries = 0;
      while (tries < 20) {
        const res = await fetch(`${apiBase}/v1/verifications/${verify.job_id}`).then(r => r.json());
        if (res.status === 'approved' || res.status === 'rejected') {
          setStatus(`Result: ${res.status}${res.message ? ` — ${res.message}` : ''}`);
          setLoading(false);
          return;
        }
        await new Promise(r => setTimeout(r, 1500));
        tries += 1;
      }
      setStatus('Result still pending. Try again later.');
    } catch (e) {
      console.error(e);
      setStatus('Upload/verification failed. Check console and API logs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ maxWidth: 480, margin: '40px auto', fontFamily: 'system-ui, sans-serif' }}>
      <h1>KYC Upload</h1>

      <label style={{ display: 'block', marginTop: 16 }}>
        Document photo (front/back PDF/JPG/PNG)
        <input type="file" accept="image/*,.pdf" onChange={onDocChange} />
      </label>

      <label style={{ display: 'block', marginTop: 16 }}>
        Selfie
        <input type="file" accept="image/*" capture="user" onChange={onSelfieChange} />
      </label>

      <button
        onClick={submit}
        disabled={loading}
        style={{ marginTop: 20, padding: '10px 16px' }}
      >
        {loading ? 'Working…' : 'Submit'}
      </button>

      <p style={{ marginTop: 16 }}>{status}</p>
    </main>
  );
}
