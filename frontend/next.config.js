/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',                  // generate pure static files to /out
  images: { unoptimized: true },     // required for export when using next/image anywhere
  reactStrictMode: true
};
module.exports = nextConfig;
