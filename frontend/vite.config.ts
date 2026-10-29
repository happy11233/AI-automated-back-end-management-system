import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    manifest: true,
    rollupOptions: {
      output: {
        onlyExplicitManualChunks: true,
        manualChunks(id) {
          // Keep synchronous shell dependencies together to avoid cycles between generated chunks.
          if (/\/src\/(App\.tsx|api\.ts|workspace\/(shared|appHelpers)\.tsx|hooks\/[^/]+\.ts|components\/(AsyncBoundary|SessionControls)\.tsx)$/.test(id)) return "application";
          if (!id.includes("/node_modules/")) return;
          if (/\/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "vendor-react";
          if (/\/node_modules\/@ant-design\/(icons|icons-svg)\//.test(id)) return "vendor-icons";
          if (/\/node_modules\/@ant-design\/(cssinjs|cssinjs-utils)\//.test(id)) return "vendor-styling";
          if (/\/node_modules\/(rc-util|rc-motion|rc-resize-observer)\//.test(id)
            || /\/node_modules\/@rc-component\/(util|context|mutate-observer|portal|trigger)\//.test(id)) {
            return "vendor-ui-core";
          }
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
