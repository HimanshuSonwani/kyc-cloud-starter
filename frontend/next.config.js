/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export', // if you’re serving as static; otherwise remove this
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
