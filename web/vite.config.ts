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
    'import.meta.env.VITE_API_URL': JSON.stringify(`${apiUrl}${apiPrefix}`),
    'import.meta.env.VITE_API_PREFIX': JSON.stringify(apiPrefix),
  },
})
