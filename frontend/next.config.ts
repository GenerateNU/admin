import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // packages/api ships raw TypeScript rather than a build step, so Next has to compile it.
  // Next 16 writes AGENTS.md/CLAUDE.md into the app dir on every dev boot; opt out.
  agentRules: false,
  transpilePackages: ["@generate-admin/api"],
};

export default nextConfig;
