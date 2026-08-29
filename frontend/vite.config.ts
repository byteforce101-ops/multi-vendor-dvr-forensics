import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],

    resolve: {
      alias: {
        "@": path.resolve(__dirname, "."),
      },
    },

    server: {
      host: "127.0.0.1",
      port: 3000,

      // Frontend → FastAPI backend
      proxy: {
        "/cases": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },

        "/evidence": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },

        "/video": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },

        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },

      // Keep your existing HMR behaviour
      hmr: process.env.DISABLE_HMR !== "true",

      watch:
        process.env.DISABLE_HMR === "true"
          ? null
          : {},
    },
  };
});