/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // REMOVE standalone build completely
  output: 'server',
};

module.exports = nextConfig;
