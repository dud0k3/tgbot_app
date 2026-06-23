import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5174,
    strictPort: false,
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '.ngrok-free.dev',
      '.ngrok-free.app',
      '.ngrok.io'
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
