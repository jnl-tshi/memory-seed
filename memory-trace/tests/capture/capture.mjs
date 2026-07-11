#!/usr/bin/env node
// Memory Trace interaction-recording harness: Playwright drives a real
// Chromium against a running memory-trace server and records native video
// (recordVideo - no manual frame stitching), then ffmpeg converts the result
// to an embeddable GIF (two-pass palette encode) alongside the source webm.
//
// Usage:
//   node capture.mjs <scenario> <server-url> <out-dir> [--no-gif]
//
// Scenarios are defined in scenarios.mjs. See README.md for setup
// (playwright + a downloaded chromium + ffmpeg on PATH).
import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import { mkdirSync, readdirSync, renameSync, rmSync } from "node:fs";
import path from "node:path";
import { SCENARIOS } from "./scenarios.mjs";

const [scenarioName, baseUrl, outDir, ...flags] = process.argv.slice(2);
const skipGif = flags.includes("--no-gif");
const ffmpegBin = process.env.FFMPEG_BIN || "ffmpeg";

function usageAndExit(message) {
  if (message) console.error(message);
  console.error(`Usage: node capture.mjs <scenario> <server-url> <out-dir> [--no-gif]`);
  console.error(`Scenarios: ${Object.keys(SCENARIOS).join(", ")}`);
  process.exit(2);
}

if (!scenarioName || !baseUrl || !outDir) usageAndExit();
const scenario = SCENARIOS[scenarioName];
if (!scenario) usageAndExit(`Unknown scenario: ${scenarioName}`);

async function main() {
  mkdirSync(outDir, { recursive: true });
  const videoDir = path.join(outDir, `.${scenarioName}-video-tmp`);
  mkdirSync(videoDir, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: videoDir, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();

  await scenario(page, baseUrl);

  const video = page.video();
  await context.close(); // finalizes the video file on disk
  await browser.close();

  const recordedPath = await video.path();
  const webmPath = path.join(outDir, `${scenarioName}.webm`);
  renameSync(recordedPath, webmPath);
  rmSync(videoDir, { recursive: true, force: true });
  console.log(`Recorded: ${webmPath}`);

  if (!skipGif) {
    const gifPath = path.join(outDir, `${scenarioName}.gif`);
    const palettePath = path.join(outDir, `.${scenarioName}-palette.png`);
    // Two-pass palette encode: ffmpeg's default GIF encoder banding-quantizes
    // badly on UI screenshots (flat colors, thin lines); generating a custom
    // palette first keeps text and hairline edges legible.
    const paletteResult = spawnSync(ffmpegBin, [
      "-y", "-i", webmPath,
      "-vf", "fps=10,scale=1440:-1:flags=lanczos,palettegen",
      palettePath,
    ], { stdio: "inherit" });
    if (paletteResult.status !== 0) {
      console.error("ffmpeg palette generation failed - is ffmpeg on PATH? (set FFMPEG_BIN to override)");
      process.exit(1);
    }
    const gifResult = spawnSync(ffmpegBin, [
      "-y", "-i", webmPath, "-i", palettePath,
      "-lavfi", "fps=10,scale=1440:-1:flags=lanczos[x];[x][1:v]paletteuse",
      gifPath,
    ], { stdio: "inherit" });
    rmSync(palettePath, { force: true });
    if (gifResult.status !== 0) {
      console.error("ffmpeg GIF encode failed.");
      process.exit(1);
    }
    console.log(`Exported: ${gifPath}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
