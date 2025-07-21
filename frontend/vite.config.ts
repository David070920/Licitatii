import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false, // Disable sourcemaps for production
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'chart-vendor': ['recharts', 'd3'],
          'map-vendor': ['leaflet', 'react-leaflet'],
          'utils-vendor': ['axios', 'date-fns', 'file-saver'],
        },
        // Optimize asset naming for better caching
        assetFileNames: 'assets/[name].[hash][extname]',
        chunkFileNames: 'assets/[name].[hash].js',
        entryFileNames: 'assets/[name].[hash].js',
      },
    },
    // Optimize build performance
    target: 'es2020',
    cssCodeSplit: true,
    // Increase chunk size warning limit for better performance
    chunkSizeWarningLimit: 1000,
  },
  // Define global constants for production
  define: {
    'process.env.NODE_ENV': '"production"',
  },
})