import { defineConfig } from "orval";

export default defineConfig({
  admin: {
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
