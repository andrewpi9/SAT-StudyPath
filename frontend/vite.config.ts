import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev the frontend talks to the API at a relative `/api` path and Vite
// proxies it to FastAPI. The static GitHub Pages build sets VITE_DEMO=1 (runs
// the app entirely in the browser) and VITE_BASE to the repo path.
// https://vite.dev/config/
export default defineConfig({
  base: process.env.VITE_BASE || '/',
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
