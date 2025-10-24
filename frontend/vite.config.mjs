// frontend/vite.config.mjs
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Read the backend URL once at dev time.
// In Codespaces, set VITE_BACKEND_URL to your forwarded 8080 URL.
// In Docker/local, you typically leave it unset and use the proxy target below.
const backend = process.env.VITE_BACKEND_URL || 'http://localhost:8080'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    // Proxy /api/* → backend so the UI can just call /api/...
    proxy: {
      '/api': {
        target: backend,
        changeOrigin: true,
        // If your Codespaces URL is HTTPS, keep secure true (default); set to false to ignore self-signed certs
        secure: true,
        rewrite: (path) => path // keep /api prefix
      }
    }
  },
  // Make the backend URL available in client code (optional)
  define: {
    'import.meta.env.VITE_BACKEND_URL': JSON.stringify(backend)
  }
})
