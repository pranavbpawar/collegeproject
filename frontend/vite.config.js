import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    // Load env vars for the current mode (development/production)
    const env = loadEnv(mode, process.cwd(), '');

    // Backend URL for the dev proxy — falls back to localhost
    const backendTarget = env.VITE_BACKEND_URL || 'http://localhost:8000';

    return {
        plugins: [react()],
        server: {
            port: 5173,
            // Allow access from VMs on the same LAN (so employees can test the dashboard too)
            host: '0.0.0.0',
            proxy: {
                '/api': {
                    target: backendTarget,
                    changeOrigin: true,
                    // Rewrite not needed — backend uses /api path
                },
            },
        },
        build: {
            outDir: 'dist',
            sourcemap: false,  // Disable in production for security
            rollupOptions: {
                output: {
                    // Chunk splitting for better caching
                    manualChunks: {
                        vendor: ['react', 'react-dom'],
                        charts: ['recharts'],
                    },
                },
            },
        },
        // Defines for compatibility — not needed since we use import.meta.env directly
        define: {},
    };
});
