// The preset registers TanStack Start, React, Tailwind, and Nitro.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import { env } from "node:process";

export default defineConfig({
  vite: {
    server: {
      proxy: {
        "/api/ask": {
          target: env["RAG_BACKEND_URL"] || "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  },
  tanstackStart: {
    // Use the SSR error wrapper in src/server.ts.
    server: { entry: "server" },
  },
});
