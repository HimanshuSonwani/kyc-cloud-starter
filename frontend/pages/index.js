// frontend/pages/index.js
import dynamic from 'next/dynamic';
const KycForm = dynamic(() => import('../components/KycForm'), { ssr: false });
export default function Home() { return <KycForm />; }
