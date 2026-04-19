import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  webpack: (config) => {
    // react-pdf uses canvas which isn't available server-side
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
