import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
  // Both dev servers run together; they must not replace each other's bundles.
  cacheDir: "node_modules/.vite/storefront",
  plugins: [vue()],
  server: {
    watch: {
      // This app also shares its workspace with the Archives build. Watching
      // that output can hold Windows directory handles open during cleanup.
      ignored: ["**/dist/**", "**/dist-archives/**", "**/.seo-verification/**"],
    },
  },
});
