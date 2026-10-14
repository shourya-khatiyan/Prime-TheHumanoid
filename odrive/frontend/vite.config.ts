import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const BACKEND = `127.0.0.1:${process.env.ODRV_PORT ?? '8765'}`
const TOKEN_FILE = resolve(import.meta.dirname, '../backend/data/.session-token')

/** dev only: inject the backend's session token so the ui can open the websocket */
function sessionToken(): Plugin {
  return {
    name: 'odrv-session-token',
    apply: 'serve',
    transformIndexHtml(html) {
      let token = ''
      try {
        token = readFileSync(TOKEN_FILE, 'utf-8').trim()
      } catch {
        // backend not started yet; the ui shows a connection error until reload
      }
      return html.replace('<!--odrv-session-->', `<meta name="odrv-token" content="${token}">`)
    },
  }
}

export default defineConfig({
  plugins: [react(), sessionToken()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/ws': { target: `ws://${BACKEND}`, ws: true },
      '/api': { target: `http://${BACKEND}` },
    },
  },
  build: { outDir: 'dist', sourcemap: false, chunkSizeWarningLimit: 900 },
})
