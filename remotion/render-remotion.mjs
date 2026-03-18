/**
 * render-remotion.mjs
 *
 * Bundles and renders a Remotion composition to mp4 programmatically.
 * No browser UI automation — uses @remotion/renderer directly.
 *
 * Usage: node render-remotion.mjs <compositionId> <audioSrc> <outputPath>
 */

import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import { fileURLToPath } from 'url';
import { resolve, dirname } from 'path';
import { copyFileSync, readdirSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const log = msg => process.stderr.write(`[remotion] ${msg}\n`);

const [,, compositionId, audioSrc, outputPath] = process.argv;
if (!compositionId || !outputPath) {
  log('Usage: node render-remotion.mjs <compositionId> <audioSrc> <outputPath>');
  process.exit(1);
}

log('Bundling...');
const bundleLocation = await bundle({
  entryPoint: resolve(__dirname, 'src/index.ts'),
  onProgress: p => process.stderr.write(`\r  bundle ${Math.round(p * 100)}%  `),
  publicDir: resolve(__dirname, 'public'),
});
process.stderr.write('\n');

// Copy public/ assets into the bundle temp dir so the local server can serve them
const publicSrc = resolve(__dirname, 'public');
try {
  for (const file of readdirSync(publicSrc)) {
    copyFileSync(resolve(publicSrc, file), resolve(bundleLocation, file));
    log(`Copied public/${file} → bundle`);
  }
} catch {}

log('Selecting composition...');
const composition = await selectComposition({
  serveUrl: bundleLocation,
  id: compositionId,
  inputProps: { audioSrc: audioSrc || '' },
});

const durationSec = (composition.durationInFrames / composition.fps).toFixed(1);
log(`Rendering ${composition.durationInFrames} frames (${durationSec}s) at ${composition.width}×${composition.height}, concurrency=4...`);

await renderMedia({
  composition,
  serveUrl: bundleLocation,
  codec: 'h264',
  outputLocation: outputPath,
  inputProps: { audioSrc: audioSrc || '' },
  concurrency: 4,
  pixelFormat: 'yuv420p',
  crf: 18,
  onProgress: ({ progress }) => process.stderr.write(`\r  render ${Math.round(progress * 100)}%  `),
});
process.stderr.write('\n');
log(`Done: ${outputPath}`);
