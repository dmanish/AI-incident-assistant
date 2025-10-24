// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Only use the proxy when VITE_BACKEND_URL is NOT set.
// In Docker: VITE_BACKEND_URL=http://api:8080 (no proxy).
// In Codespaces: VITE_BACKEND_URL=https://<codespace>-8080.app.github.dev (no proxy).
// In plain local dev: leave it unset and the proxy will forward /api -> http://localhost:8080.
const backend = process.env.VITE_BACKEND_URL

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: !backend
      ? {
          '/api': {
            target: 'http://localhost:8080',
            changeOrigin: true,
            secure: false,
            rewrite: (path) => path.replace(/^\/api/, ''), // '/api/login' -> '/login'
          },
        }
      : undefined,
  },
})

