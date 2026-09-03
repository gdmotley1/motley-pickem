import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages serves this from /cfb-pickem/. Set BASE=/ for a custom domain later.
const base = process.env.BASE ?? '/cfb-pickem/'

export default defineConfig({
  base,
  // static/ holds the vendored logos, the manifest and mock data.
  publicDir: 'static',
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsInlineLimit: 0, // keep logos as real files so the service worker can cache them
  },
  server: { port: 5173, host: true },
})
