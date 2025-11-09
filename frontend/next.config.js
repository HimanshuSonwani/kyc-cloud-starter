/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',             // replaces `next export`
  images: { unoptimized: true } // optional: avoids Image Optimization on static hosts
};
module.exports = nextConfig;
