/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',          // static export → no SSR, no 502
  images: { unoptimized: true },
  reactStrictMode: true
};

export default nextConfig;
