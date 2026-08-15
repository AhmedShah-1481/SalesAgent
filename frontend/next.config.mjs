/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    // Company logos via Clearbit (free, no key) — PROJECT_BRIEF.md.
    remotePatterns: [{ protocol: "https", hostname: "logo.clearbit.com" }],
  },
};

export default nextConfig;
