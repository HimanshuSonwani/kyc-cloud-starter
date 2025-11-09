/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // produce the .next/standalone server.js that we run on Railway
  output: 'standalone'
};

module.exports = nextConfig;
