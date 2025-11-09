/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // we are serving as static; export is configured here (do not run `next export`)
  output: 'export',
  images: { unoptimized: true },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://kyc-cloud-starter-production.up.railway.app/:path*',
      },
    ];
  },
};
module.exports = nextConfig;
