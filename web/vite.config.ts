import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// On GitHub Pages the site lives at /<repo-name>/, so the deploy workflow sets VITE_BASE.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react(), tailwindcss()],
  build: { chunkSizeWarningLimit: 800 }, // one ~200 KB gzipped bundle is fine for this site
});
