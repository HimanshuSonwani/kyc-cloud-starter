// frontend/components/HealthCheck.jsx
import { useState } from "react";
import { apiGet } from "../lib/api";

export default function HealthCheck() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  const check = async () => {
    setError(""); setStatus(null);
    try {
      const data = await apiGet("/api/health");
      setStatus(JSON.stringify(data));
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="p-3 border rounded">
      <button onClick={check}>Ping /api/health</button>
      {status && <p style={{color:"green"}}>OK: {status}</p>}
      {error && <p style={{color:"crimson"}}>ERR: {error}</p>}
    </div>
  );
}
