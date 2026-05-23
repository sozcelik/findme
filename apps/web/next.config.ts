import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@findme/types", "@findme/api-contract"],
};

export default nextConfig;
