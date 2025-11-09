/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',          // replaces "next export"
  images: { unoptimized: true }, // needed if you use <Image/> with static export
  trailingSlash: true        // optional; keeps urls consistent when served from /out
};

module.exports = nextConfig;
