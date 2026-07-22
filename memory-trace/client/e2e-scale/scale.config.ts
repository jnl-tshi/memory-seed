import { defineConfig, devices } from "@playwright/test";

// Measurement harness ONLY. Points at a server started by hand from the
// b0b-topology-scale worktree on port 8791 (NOT 8756, which serves the main
// checkout). No webServer block, no reuse ambiguity.
export default defineConfig({
  testDir: ".",
  testMatch: /scale\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  timeout: 600_000,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:8791", trace: "off" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
