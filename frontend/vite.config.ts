import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// API URL: use env var in Docker (api:8000) or localhost for local dev
const apiTarget = process.env.VITE_API_URL || 'http://localhost:8000'
const wsTarget = apiTarget.replace('http', 'ws')

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: wsTarget,
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ws/, ''),
      },
    },
  },
})

