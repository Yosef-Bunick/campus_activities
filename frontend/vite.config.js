import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// The API's origin, baked into the service worker so it can keep an offline
// copy of the last answers (ADR-031). Same default as src/api.js.
const API_BASE = (process.env.VITE_API_BASE || 'http://localhost:8000').replace(/\/$/, '')
const escapeRe = (t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const API_READS = new RegExp(`^${escapeRe(API_BASE)}/(events|rooms|favorites|hidden|alerts|auth/me|auth/majors)(\\?|$)`)

export default defineConfig({
  plugins: [
    react(),
    // PWA: manifest + Workbox service worker, so the app can be added to the
    // home screen. Off in `npm run dev` (a dev SW caches stale code); check it
    // with `npm run build && npm run preview`.
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'script-defer',
      includeManifestIcons: false, // already matched by globPatterns below
      manifest: {
        name: 'Campus Events',
        short_name: 'Campus Events',
        description: "What's happening on campus right now",
        start_url: '/home',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#ffffff',
        theme_color: '#1976d2',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/icons/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Precache only the shell + icons. Page chunks are cached the first time
        // they're opened, so the service worker never pulls /map code in the
        // background for someone who never opens the map.
        globPatterns: ['index.html', 'registerSW.js', 'favicon.ico', 'icons/*.png'],
        navigateFallback: '/index.html',
        runtimeCaching: [
          {
            // Offline (Phase 2): try the network for up to 4 s, else show the
            // last answer. Per-person data, so sign-out deletes this cache.
            urlPattern: API_READS,
            method: 'GET',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api',
              networkTimeoutSeconds: 4,
              expiration: { maxEntries: 80, maxAgeSeconds: 7 * 24 * 3600 },
              cacheableResponse: { statuses: [200] },
            },
          },
          {
            // Hashed, immutable build output.
            urlPattern: ({ sameOrigin, url }) => sameOrigin && url.pathname.startsWith('/assets/'),
            handler: 'CacheFirst',
            options: { cacheName: 'assets', expiration: { maxEntries: 60 } },
          },
        ],
      },
    }),
  ],
  server: { port: 5173, strictPort: true },
  build: {
    // dist/.vite/manifest.json lets scripts/check-size.mjs find the first-load chunks.
    manifest: true,
    rollupOptions: {
      output: {
        // Same vendor split as unified's ledger-ui/vite.config.js.
        manualChunks: (id) => {
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) return 'vendor-react'
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/__tests__/**/*.test.{js,jsx}'],
  },
})
