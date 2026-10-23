import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Served from https://parbproject.github.io/portfolio-risk-lab/
export default defineConfig({
  base: "/portfolio-risk-lab/",
  plugins: [react()],
  build: { target: "es2022", outDir: "dist", emptyOutDir: true },
});
