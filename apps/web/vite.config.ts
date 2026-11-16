import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icons/*.svg', 'offline.html'],
      manifest: {
        name: '私人健身教练',
        short_name: '健身教练',
        description: 'AI 驱动的个性化健身训练应用',
        lang: 'zh-CN',
        display: 'standalone',
        orientation: 'portrait-primary',
        theme_color: '#4f46e5',
        background_color: '#f4f5fa',
        icons: [
          {
            src: 'icons/icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any'
          },
          {
            src: 'icons/icon-maskable.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'maskable'
          }
        ]
      },
      workbox: {
        // Only precache the app shell & static assets (plan §4.7).
        // /api/** responses are NEVER cached — private data lives
        // exclusively in the per-user IndexedDB.
        globPatterns: ['**/*.{js,css,html,ico,svg}'],
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api\//]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
