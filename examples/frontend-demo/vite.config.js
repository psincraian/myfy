import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    tailwindcss() // Auto-scans frontend/templates/**/*.html
  ],

  build: {
    outDir: 'frontend/static/dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        main: 'frontend/js/main.js',
        'theme-switcher': 'frontend/js/theme-switcher.js',
        styles: 'frontend/css/input.css'
      },
      output: {
        entryFileNames: 'js/[name]-[hash].js',
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name.endsWith('.css')) {
            return 'css/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        }
      }
    }
  },

  server: {
    port: 3001,
    cors: true,
    strictPort: false
  }
})
