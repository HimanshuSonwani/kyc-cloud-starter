// frontend/pages/index.js
import dynamic from 'next/dynamic';

// Load the upload UI only in the browser (avoids "File is not defined" during SSR)
const KycForm = dynamic(() => import('../components/KycForm'), { ssr: false });

export default function Home() {
  return <KycForm />;
}
