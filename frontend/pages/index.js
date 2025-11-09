// frontend/pages/index.js

import dynamic from 'next/dynamic';

// Load the upload UI only in the browser (no SSR → avoids "File is not defined")
const KycForm = dynamic(() => import('../components/KycForm'), {
  ssr: false, // <<< This prevents Next.js from server-rendering the component
});

export default function Home() {
  return <KycForm />;
}
