// frontend/pages/index.js
import dynamic from 'next/dynamic';

// Load the upload UI only in the browser (no SSR → avoids "File is not defined")
const KycForm = dynamic(() => import('../components/KycForm'), { ssr: false });

// Force SSR instead of static export so Next.js does NOT try to prerender this
// page at build time (that’s where the 'File is not defined' came from).
export async function getServerSideProps() {
  return { props: {} };
}

export default function Home() {
  return <KycForm />;
}
