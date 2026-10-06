// JS size budget (architecture §3): gzipped JS needed for the FIRST load must
// stay under ~150 KB. "First load" = the entry chunk plus everything it imports
// statically. Lazy pages (dynamic imports) are excluded — that's the point.
// Run after `npm run build`.
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';

const BUDGET_KB = 150;
const manifest = JSON.parse(readFileSync('dist/.vite/manifest.json', 'utf8'));

const seen = new Set();
function walk(key) {
  if (seen.has(key)) return;
  seen.add(key);
  for (const dep of manifest[key].imports || []) walk(dep);
}
for (const [key, chunk] of Object.entries(manifest)) if (chunk.isEntry) walk(key);

let total = 0;
for (const key of seen) {
  const file = manifest[key].file;
  const kb = gzipSync(readFileSync(`dist/${file}`)).length / 1024;
  total += kb;
  console.log(`${kb.toFixed(1).padStart(7)} KB  ${file}`);
}
console.log(`${total.toFixed(1).padStart(7)} KB  first-load JS, gzipped (budget ${BUDGET_KB} KB)`);
if (total > BUDGET_KB) {
  console.error(`FAIL: over the ${BUDGET_KB} KB budget`);
  process.exit(1);
}
