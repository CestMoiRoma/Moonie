import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// During `npm run dev`, proxy /api to the FastAPI backend so the SPA and API
// share an origin. In production FastAPI serves the built files directly.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
