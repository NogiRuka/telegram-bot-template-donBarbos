import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import dotenv from 'dotenv'

// https://vite.dev/config/
// 从仓库根目录加载 .env，统一 API_HOST/API_PORT/WEB_PORT
dotenv.config({ path: path.resolve(__dirname, '../.env') })

const apiHost = process.env.API_HOST ?? '127.0.0.1'
const apiPort = Number(process.env.API_PORT ?? '8000')
const webPort = Number(process.env.WEB_PORT ?? '3000')
const apiUrl = `http://${apiHost}:${apiPort}`
const apiPrefix = '/api'

export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: webPort,
    host: true,
    proxy: {
      '/api': {
        target: apiUrl,
        changeOrigin: true,
      },
    },
  },
  define: {
    // 强制使用相对路径 /api，让浏览器通过当前访问的域名（前端服务器）进行代理转发
    // 而不是直接访问后端 IP（避免 0.0.0.0 或 CORS 问题）
    'import.meta.env.VITE_API_URL': JSON.stringify(apiPrefix),
    'import.meta.env.VITE_API_PREFIX': JSON.stringify(apiPrefix),
  },
})
