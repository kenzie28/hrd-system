import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE_PATH || '/',
  server: {
    port: 5128,
    proxy: {
      // Local dev: SPA uses /api → Django on :8028 (no API key in dev/dev.sh).
      '/api': {
        target: 'http://127.0.0.1:8028',
        changeOrigin: true,
      },
    },
  },
})
