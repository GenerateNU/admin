import { defineConfig } from "orval";

export default defineConfig({
  admin: {
    // Reads the live schema, so the backend needs to be running when you `npm run gen`.
    input: { target: "http://localhost:8000/openapi.json" },
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
