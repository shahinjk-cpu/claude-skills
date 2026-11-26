#!/usr/bin/env node
// Check the Google Play store listing text (store-assets/listing.json) and the text inside preview assets
// (screenshot captions, chips, callout labels from plan.json) against Play's limits and metadata policy,
// then write play-store/store-listing.md, ready to paste into Play Console.
// Usage: node listing.mjs [--dir store-assets]          exit code 1 when there are errors
//
// listing.json: { "language": "en-US", "title": "...", "short": "...", "full": "...", "releaseNotes": "...",
//                 "category": "Action", "tags": ["Runner", "Dinosaur"], "contactEmail": "", "website": "" }
import fs from 'node:fs';
import path from 'node:path';
import { args, outDir } from './lib.mjs';

const a = args();
const dir = path.resolve(a.dir || outDir());
const R = p => path.join(dir, p);
if (!fs.existsSync(R('listing.json'))) { console.error('No listing.json in ' + dir); process.exit(1); }
const L = JSON.parse(fs.readFileSync(R('listing.json'), 'utf8'));
const plan = fs.existsSync(R('plan.json')) ? JSON.parse(fs.readFileSync(R('plan.json'), 'utf8')) : {};
const brand = fs.existsSync(R('brand.json')) ? JSON.parse(fs.readFileSync(R('brand.json'), 'utf8')) : {};
const errors = [], warnings = [];

// Google Play limits (characters)
const LIMITS = { title: 30, short: 80, full: 4000, releaseNotes: 500 };
for (const [k, max] of Object.entries(LIMITS)) {
  const v = L[k] || '';
  if (!v && k !== 'releaseNotes') errors.push(`${k} is empty`);
  if ([...v].length > max) errors.push(`${k}: ${[...v].length}/${max} characters`);
}

// Metadata policy terms (title / icon / developer name: not allowed; preview assets + descriptions: avoid)
// title (and icon/developer name): strict, any of these words is a policy problem
const RANKING_STRICT = /(#\s?1\b|\bno\.?\s?1\b|number one|\bbest\b|\btop\b|\bpopular\b|of the year|best of play|award|editor'?s'? choice|\bwinner\b|trending|\bhit\b)/i;
const PROMO_STRICT = /(\bfree\b|\bsale\b|discount|% ?off|\bcheap\b|\bdeal\b|limited time|download now|install now|\bbonus\b|\bnew\b|\bhot\b|\bpromo\b|\$\d|€\d|£\d|\bprice\b)/i;
// descriptions and preview-asset text: only real claims ("your best distance" and "a new level" are fine)
const RANKING_SOFT = /(#\s?1\b|\bno\.?\s?1\b|number one|\bthe best\b|\bbest (game|app|runner|puzzle|rpg|shooter|racing|game ever|mobile)|\btop[- ]?(rated|\d+|game|app|charts?)\b|\bmost popular\b|of the year|best of play|award[- ]winning|editor'?s'? choice)/i;
const PROMO_SOFT = /(\bsale\b|discount|% ?off|\bcheap\b|limited time|download now|install now|\$\d|€\d|£\d)/i;
const BUZZ_ASSET = /(\bfree\b|\bbest\b|#\s?1\b|\bsale\b|discount|download now)/i;   // Play: keep "free"/"best" out of preview assets
const PROGRAMS = /(google play|play pass|play points|editor'?s'? choice|teacher approved)/i;
const EMOJI = /\p{Extended_Pictographic}/u;
const REPEAT_SPECIAL = /([!?*#$%&@~^+=|_.\-])\1{1,}/;
const brandWords = new Set(String(brand.name || L.title || '').split(/[^A-Za-z0-9]+/).filter(Boolean).map(w => w.toUpperCase()));

// mode: 'title' (errors) | 'text' (descriptions: warnings) | 'asset' (screenshot / feature graphic text: warnings)
function scan(text, where, mode) {
  if (!text) return;
  const push = (m) => (mode === 'title' ? errors : warnings).push(`${where}: ${m}`);
  let m;
  const [rank, promo] = mode === 'title' ? [RANKING_STRICT, PROMO_STRICT] : [RANKING_SOFT, PROMO_SOFT];
  if ((m = text.match(rank))) push(`ranking/award wording "${m[0]}" (Play metadata policy)`);
  if ((m = text.match(promo))) push(`price/promotional wording "${m[0]}"`);
  if (mode === 'asset' && (m = text.match(BUZZ_ASSET)) && !(text.match(rank) || text.match(promo))) push(`buzzword "${m[0]}" (Play asks to keep it out of preview assets)`);
  if ((m = text.match(PROGRAMS))) push(`refers to a Google Play program/brand "${m[0]}"`);
  if (mode === 'title') {
    if (EMOJI.test(text)) push('emoji (not allowed in the title)');
    if (REPEAT_SPECIAL.test(text)) push('repeated special characters');
    const caps = text.split(/[^A-Za-z]+/).filter(w => w.length >= 4 && w === w.toUpperCase() && !brandWords.has(w));
    if (caps.length) push(`ALL CAPS word(s) ${caps.slice(0, 3).join(', ')} (allowed only as part of a brand name)`);
  }
}
scan(L.title, 'title', 'title');
scan(L.short, 'short description', 'text');
scan(L.full, 'full description', 'text');
scan(L.releaseNotes, 'release notes', 'text');

// Full description quality checks
if (L.full) {
  const words = L.full.toLowerCase().match(/[a-z']{4,}/g) || [];
  const counts = words.reduce((m, w) => (m[w] = (m[w] || 0) + 1, m), {});
  const stop = new Set(['your', 'with', 'from', 'that', 'this', 'they', 'them', 'have', 'into', 'more', 'each', 'every', 'their', 'will', 'what', 'when', 'than', 'then', 'like', 'just', 'over', 'game']);
  for (const [w, c] of Object.entries(counts)) if (!stop.has(w) && c >= 8 && c / words.length > 0.025) warnings.push(`full description repeats "${w}" ${c} times (keyword stuffing is against Play policy)`);
  if (/"[^"]{10,}"\s*[-–—]\s*\w+/.test(L.full) || /\b(5 stars|five stars|★★★★★)\b/i.test(L.full)) warnings.push('full description looks like it contains testimonials or ratings: only attributed quotes are allowed');
  if (/https?:\/\//i.test(L.full)) warnings.push('full description contains a URL: put links in the website field instead');
  const first = L.full.slice(0, 167);
  if (!/[.!?]/.test(first)) warnings.push('the first 167 characters (shown before "more") should be a complete hook sentence');
}

// Text inside preview assets (screenshots, feature graphic): Play asks to avoid buzzwords like "free" and "best"
for (const [i, s] of (plan.screenshots || []).entries()) {
  const texts = [s.headline, s.sub, s.badge, ...(s.chips || []).map(c => typeof c === 'string' ? c : c.text), s.callout?.label].filter(Boolean).map(t => t.replace(/\*/g, ''));
  for (const t of texts) scan(t, `screenshot ${i + 1} text "${t}"`, 'asset');
}
if (plan.feature?.sub) scan(plan.feature.sub, 'feature graphic text', 'asset');

// Write the paste-ready listing
const out = R('play-store/store-listing.md');
fs.mkdirSync(path.dirname(out), { recursive: true });
const md = `# ${L.title} — Google Play store listing (${L.language || 'en-US'})

Paste each block into Play Console > Grow users > Store presence > Main store listing.

## App name (${[...(L.title || '')].length}/30)
${L.title || ''}

## Short description (${[...(L.short || '')].length}/80)
${L.short || ''}

## Full description (${[...(L.full || '')].length}/4000)
${L.full || ''}
${L.releaseNotes ? `\n## Release notes (${[...L.releaseNotes].length}/500)\n${L.releaseNotes}\n` : ''}${L.category ? `\n## Category\nGame > ${L.category}\n` : ''}${(L.tags || []).length ? `\n## Tags (pick up to 5 in Play Console)\n${L.tags.join(', ')}\n` : ''}
## Graphics
- App icon: \`icon-512.png\`
- Feature graphic: \`feature-graphic-1024x500.png\`
- Phone screenshots: \`screenshots/\` (upload in order)${fs.existsSync(R('play-store/screenshots-7inch')) ? '\n- 7-inch tablet screenshots: `screenshots-7inch/`\n- 10-inch tablet screenshots: `screenshots-10inch/`' : ''}
`;
fs.writeFileSync(out, md);

for (const e of errors) console.log('✗ ' + e);
for (const w of warnings) console.log('⚠ ' + w);
console.log(errors.length ? `\n${errors.length} error(s): fix listing.json before publishing.` : warnings.length ? '\nNo errors. Review the warnings.' : '\nListing text OK ✓');
console.log('Wrote ' + out);
process.exit(errors.length ? 1 : 0);
