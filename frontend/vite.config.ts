import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
  plugins: [vue()],
  server: {
    watch: {
      // This app also shares its workspace with the Archives build. Watching
      // that output can hold Windows directory handles open during cleanup.
      ignored: ["**/dist/**", "**/dist-archives/**", "**/.seo-verification/**"],
    },
  },
});
