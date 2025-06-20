import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// PORT environment variable set in sirepo.pkcli.service
const port = process.env.PORT || 8008;

// https://vite.dev/config/
export default defineConfig({
    plugins: [
        vue(),
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
            '/static': fileURLToPath(new URL('../sirepo/package_data/static', import.meta.url))
        },
    },
    server: {
        port: port,
        hmr: {
            port: port,
        },
    },
})
