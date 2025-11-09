import dynamic from 'next/dynamic';
const KycForm = dynamic(() => import('../components/KycForm'), { ssr: false });

export default function Home() {
  return (
    <main style={{padding: 24, fontFamily: 'system-ui, Arial'}}>
      <h1>KYC Upload</h1>
      <KycForm />
    </main>
  );
}
