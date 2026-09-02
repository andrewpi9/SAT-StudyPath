import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The frontend talks to the API at a relative `/api` path; in dev, Vite proxies
// that to the FastAPI server so there are no CORS surprises and no base-URL config.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
