import type { NextConfig } from 'next';

const config: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  // Resolve metadata/notFound before sending headers, preserving real HTTP 404.
  htmlLimitedBots: /.*/,
};

export default config;
