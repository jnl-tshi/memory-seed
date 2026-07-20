import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

// The e2e harness runs against the packaged React build (../memory_trace/static/react),
// served by the real `memory-trace` CLI over the actual retrieval service - not a mock,
// not the Vite dev server. This is what "packaged-wheel loading" (design-system proposal
// section 11) means: prove the shipped artifact works, not just source under Vite.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..");
const PORT = 8756;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: `npm run build --prefix "${__dirname}" && ` +
      `python -m memory_trace.cli --cwd "${repoRoot}" --host 127.0.0.1 --port ${PORT} --no-open`,
    // memory_trace (memory-trace/memory_trace) imports memory_seed (repo root) - neither
    // package is pip-installed in this dev environment, so both roots must be on the path.
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "memory-trace")].join(path.delimiter),
    },
    url: `http://127.0.0.1:${PORT}/next`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
