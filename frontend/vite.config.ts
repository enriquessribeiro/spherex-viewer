import { defineConfig } from "vite";

export default defineConfig({
  // Caminhos relativos: o site é publicado em https://<usuario>.github.io/spherex-viewer/
  base: "./",
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
