import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';
import { cloudflare } from '@cloudflare/vite-plugin';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    svelte(),
    cloudflare(),
    // PWA shell: the manifest lives in public/ (reviewed, tested), this
    // plugin only generates the service worker. Offline strategy: precache
    // the app shell, NetworkFirst for worker data (/snapshot,
    // /history-states) so revisits render the last sync when offline.
    VitePWA({
      manifest: false,
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,webmanifest,png,svg,woff2}'],
        navigateFallback: 'index.html',
        cleanupOutdatedCaches: true,
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname === '/snapshot',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'reps-snapshot',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 4, maxAgeSeconds: 86400 },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname === '/history-states',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'reps-history-states',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 4, maxAgeSeconds: 86400 },
            },
          },
        ],
      },
    }),
  ],
  build: {
    minify: 'esbuild',
  },
});
