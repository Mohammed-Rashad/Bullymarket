import type { NextConfig } from "next";

// Same-origin deployment: the browser only ever talks to this server, which
// forwards API and media requests to the backend over the internal network.
// Public URLs never appear here, so changing a domain never needs a rebuild.
const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiProxyTarget}/api/:path*` },
      { source: "/media/:path*", destination: `${apiProxyTarget}/media/:path*` },
    ];
  },
};

export default nextConfig;
