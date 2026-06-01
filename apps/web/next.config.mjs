import path from "node:path";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@ib-desk/shared"],
  // Pin the file-tracing root to the monorepo root. Without this, Next can infer
  // the wrong workspace root when other lockfiles exist higher up the tree.
  outputFileTracingRoot: path.join(import.meta.dirname, "..", ".."),
};

export default nextConfig;
