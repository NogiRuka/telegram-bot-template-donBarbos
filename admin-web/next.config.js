/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用输出文件跟踪以减少 Docker 镜像大小
  output: 'standalone',
  
  // 实验性功能
  experimental: {
    // 启用服务器组件
    serverComponentsExternalPackages: [],
  },

  // 图片优化配置
  images: {
    domains: ['localhost'],
    unoptimized: process.env.NODE_ENV === 'development',
  },

  // 环境变量配置
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },

  // 重定向配置
  async redirects() {
    return [
      {
        source: '/admin',
        destination: '/dashboard',
        permanent: true,
      },
    ];
  },

  // 重写配置
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL || 'http://localhost:5000/api'}/:path*`,
      },
    ];
  },

  // 头部配置
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ];
  },

  // Webpack 配置
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // 自定义 webpack 配置
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    }

    return config;
  },

  // 编译器选项
  compiler: {
    // 移除 console.log（仅在生产环境）
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // 性能配置
  poweredByHeader: false,
  compress: true,

  // TypeScript 配置
  typescript: {
    // 在构建时忽略 TypeScript 错误（不推荐在生产环境使用）
    ignoreBuildErrors: false,
  },

  // ESLint 配置
  eslint: {
    // 在构建时忽略 ESLint 错误（不推荐在生产环境使用）
    ignoreDuringBuilds: false,
  },
};

module.exports = nextConfig;