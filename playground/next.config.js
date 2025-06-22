const createNextPluginPreval = require("next-plugin-preval/config");
const withNextPluginPreval = createNextPluginPreval();

/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: '/playground',
  trailingSlash: true,
  reactStrictMode: false,
};

module.exports = withNextPluginPreval(nextConfig);
