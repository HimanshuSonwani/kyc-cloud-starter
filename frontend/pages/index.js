// frontend/pages/index.js
import dynamic from "next/dynamic";
const HealthCheck = dynamic(() => import("../components/HealthCheck"), { ssr: false });

export default function Home() {
  return (
    <main style={{maxWidth: 720, margin: "40px auto", fontFamily: "sans-serif"}}>
      <h1>KYC Frontend — Step 1</h1>
      <p>Verify connectivity to backend first.</p>
      <HealthCheck />
    </main>
  );
}
