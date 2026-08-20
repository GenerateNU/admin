import { defineConfig } from "orval";

export default defineConfig({
  admin: {
    // The committed schema, not a live server: `just openapi` regenerates it without booting
    // anything, and a second repo can point orval at this same file over a raw GitHub URL.
    input: { target: "../../openapi.json" },
    output: {
      mode: "tags-split",
      target: "./src/generated/endpoints.ts",
      schemas: "./src/generated/model",
      client: "react-query",
      httpClient: "fetch",
      clean: true,
      prettier: false,
      override: {
        mutator: { path: "./src/http.ts", name: "apiFetch" },
      },
    },
  },
});
