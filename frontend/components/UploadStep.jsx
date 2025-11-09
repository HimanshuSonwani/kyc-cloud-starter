import { useState } from "react";

export default function UploadStep() {
  const [files, setFiles] = useState({ front:null, back:null, selfie:null });
  const [job, setJob] = useState(null);
  const API = process.env.NEXT_PUBLIC_API_BASE;

  const onPick = (k) => (e) => setFiles((s) => ({ ...s, [k]: e.target.files[0] }));

  async function startUpload() {
    // 1) presign
    const pres = await fetch(`${API}/v1/presign`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ document_type: "aadhaar_offline", user_fields: {} })
    }).then(r => r.json());

    // 2) PUT each file to its URL
    await Promise.all(
      ["front","back","selfie"].map(async (k) => {
        if (!files[k]) return;
        await fetch(pres.upload_urls[k], {
          method: "PUT",
          headers: { "Content-Type": "image/jpeg" },
          body: files[k],
        });
      })
    );

    // 3) create verification job
    const ver = await fetch(`${API}/v1/verifications`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        document_type: "aadhaar_offline",
        object_keys: pres.object_keys,
        user_fields: {}
      })
    }).then(r => r.json());

    setJob(ver);
  }

  return (
    <div style={{marginTop:20}}>
      <div>
        <label>Front: </label><input type="file" accept="image/*" onChange={onPick("front")} />
      </div>
      <div>
        <label>Back: </label><input type="file" accept="image/*" onChange={onPick("back")} />
      </div>
      <div>
        <label>Selfie: </label><input type="file" accept="image/*" onChange={onPick("selfie")} />
      </div>
      <button onClick={startUpload} style={{marginTop:12}}>Upload & Create Job</button>
      {job && <pre style={{marginTop:12}}>{JSON.stringify(job,null,2)}</pre>}
    </div>
  );
}
