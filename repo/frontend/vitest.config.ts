import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "happy-dom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/unit/**/*.test.ts", "tests/unit/**/*.test.tsx"],
    exclude: ["./tests/e2e/**", "./**/dist/**", "./**/node_modules/**"],
    restoreMocks: true,
    clearMocks: true,
  },
});
