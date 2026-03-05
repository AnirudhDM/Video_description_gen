/**
 * headless-render.mjs
 *
 * 1. Starts Vite dev server
 * 2. Opens Motion Canvas in headless Chromium via Puppeteer
 * 3. Clicks the Render button, waits for PNG frames in output/project/
 * 4. Assembles frames + audio into an mp4 via ffmpeg
 * 5. Writes the mp4 to the path given as argv[3]
 *
 * Usage: node headless-render.mjs <scene_name> <audio_path> <output_mp4_path>
 */

import puppeteer from 'puppeteer';
import {spawn, spawnSync} from 'node:child_process';
import {existsSync, readdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {setTimeout as sleep} from 'node:timers/promises';
import {fileURLToPath} from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

const [,, sceneName, audioPath, outputPath] = process.argv;
if (!sceneName || !outputPath) {
  console.error('Usage: node headless-render.mjs <scene_name> <audio_path> <output_mp4_path>');
  process.exit(1);
}

const FRAMES_DIR = resolve(__dirname, 'output', 'project');
const PORT = 9753;
const RENDER_TIMEOUT_MS = 10 * 60 * 1000;

function log(msg) { process.stderr.write(`[headless] ${msg}\n`); }

// ── Start Vite ───────────────────────────────────────────────────────────────
log('Starting Vite...');
const vite = spawn('npx', ['vite', '--port', String(PORT), '--strictPort'], {
  cwd: __dirname,
  stdio: ['ignore', 'pipe', 'pipe'],
});
vite.on('error', err => { log(`Vite error: ${err.message}`); process.exit(1); });

await new Promise((resolve, reject) => {
  const to = setTimeout(() => reject(new Error('Vite did not start in 30s')), 30_000);
  const check = d => {
    if (d.toString().includes('localhost')) { clearTimeout(to); resolve(); }
  };
  vite.stdout.on('data', check);
  vite.stderr.on('data', check);
});
log('Vite ready.');

// ── Puppeteer ────────────────────────────────────────────────────────────────
async function renderWithBrowser() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  page.on('pageerror', e => log(`Page error: ${e.message}`));

  try {
    await page.goto(`http://localhost:${PORT}`, {waitUntil: 'networkidle0', timeout: 30_000});
    await sleep(4000);

    // Set resolution to 1280×720 (halves frame size vs 1920×1080)
    await page.evaluate(() => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      const nums = [...document.querySelectorAll('input[type="number"]')];
      const w = nums.find(i => i.value === '1920');
      const h = nums.find(i => i.value === '1080');
      if (w) { setter.call(w, '1280'); w.dispatchEvent(new Event('input', {bubbles: true})); }
      if (h) { setter.call(h, '720');  h.dispatchEvent(new Event('input', {bubbles: true})); }
    });
    await sleep(300);

    // Click render
    const clicked = await page.evaluate(() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.textContent?.trim() === 'Render');
      if (btn) { btn.click(); return true; }
      return false;
    });

    if (!clicked) {
      const buttons = await page.evaluate(() =>
        [...document.querySelectorAll('button')].map(b => b.textContent?.trim())
      );
      log(`Could not find Render button. Buttons: ${JSON.stringify(buttons)}`);
      return false;
    }

    log('Render started, waiting for completion...');

    // Poll until button returns to "Render" (meaning render finished)
    const deadline = Date.now() + RENDER_TIMEOUT_MS;
    let done = false;
    while (Date.now() < deadline) {
      await sleep(1500);
      done = await page.evaluate(() =>
        [...document.querySelectorAll('button')].some(b => b.textContent?.trim() === 'Render')
      );
      if (done) break;
    }

    if (!done) { log('Render timed out.'); return false; }
    log('Render complete.');
    return true;
  } finally {
    await browser.close().catch(() => {});
    vite.kill('SIGTERM');
  }
}

const ok = await renderWithBrowser();
if (!ok) { process.exit(1); }

// ── Assemble frames → mp4 with ffmpeg ───────────────────────────────────────
if (!existsSync(FRAMES_DIR) || readdirSync(FRAMES_DIR).length === 0) {
  log(`No frames found in ${FRAMES_DIR}`);
  process.exitCode = 1;
  process.exit();
}

const ffmpegArgs = [
  '-y',
  '-framerate', '30',
  '-i', resolve(FRAMES_DIR, '%06d.png'),
  ...(audioPath && existsSync(audioPath) ? ['-i', audioPath] : []),
  '-c:v', 'libx264',
  '-pix_fmt', 'yuv420p',
  '-crf', '18',
  ...(audioPath && existsSync(audioPath) ? ['-c:a', 'aac', '-b:a', '192k', '-shortest'] : []),
  '-movflags', '+faststart',
  outputPath,
];

log(`Running ffmpeg: ${ffmpegArgs.join(' ')}`);
const ff = spawnSync('ffmpeg', ffmpegArgs, {stdio: 'inherit'});
if (ff.status !== 0) {
  log(`ffmpeg failed with exit code ${ff.status}`);
  process.exitCode = 1;
} else {
  log(`Done: ${outputPath}`);
  process.exitCode = 0;
}
