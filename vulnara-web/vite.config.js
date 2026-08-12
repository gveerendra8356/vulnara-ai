import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/vulnara-ai/",  // Must match your GitHub repo name for GitHub Pages
  server: {
    port: 5173,
  },
});
