#!/usr/bin/env node
// Google Play publish-readiness report for a Capacitor or Unity game. Read-only: never changes the project.
// Usage: node readiness.mjs [projectDir] [--apk path/to/app.apk|.aab] [--out store-assets/play-store/publish-checklist.md]
// Checks what Play enforces at upload (target SDK, 64-bit + 16 KB native code, version code) and what commonly
// blocks or delays review (sensitive permissions, unused plugins, debuggable builds, placeholder ids).
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { args, projectRoot } from './lib.mjs';

const a = args();
const root = path.resolve(a._[0] || projectRoot());
const has = p => fs.existsSync(path.join(root, p));
const read = p => { try { return fs.readFileSync(path.join(root, p), 'utf8'); } catch { return ''; } };
const rows = [];           // [status, check, detail]   status: ok | warn | fail | info
const add = (status, check, detail) => rows.push([status, check, detail]);

// Google Play target API rule (developer.android.com/google/play/requirements/target-sdk):
// since 2026-08-31 new apps and updates must target API 36 (Android 16).
const REQUIRED_TARGET = 36, REQUIRED_SINCE = '2026-08-31';
const SENSITIVE = {
  CAMERA: 'camera', RECORD_AUDIO: 'microphone', ACCESS_FINE_LOCATION: 'precise location', ACCESS_COARSE_LOCATION: 'location',
  ACCESS_BACKGROUND_LOCATION: 'background location (needs a Play declaration)', READ_CONTACTS: 'contacts', READ_SMS: 'SMS (restricted)',
  SEND_SMS: 'SMS (restricted)', READ_CALL_LOG: 'call log (restricted)', READ_EXTERNAL_STORAGE: 'storage', WRITE_EXTERNAL_STORAGE: 'storage',
  READ_MEDIA_IMAGES: 'photos (needs a Play declaration)', READ_MEDIA_VIDEO: 'videos (needs a Play declaration)', MANAGE_EXTERNAL_STORAGE: 'all files access (restricted)',
  QUERY_ALL_PACKAGES: 'installed apps (restricted)', REQUEST_INSTALL_PACKAGES: 'install packages (restricted)', SYSTEM_ALERT_WINDOW: 'draw over apps',
  USE_FULL_SCREEN_INTENT: 'full-screen intents (needs a Play declaration)', 'com.google.android.gms.permission.AD_ID': 'advertising ID (declare in Play Console)',
};

let engine = 'unknown';
if (has('ProjectSettings/ProjectSettings.asset')) engine = 'unity';
else if (has('capacitor.config.json') || has('capacitor.config.ts') || has('capacitor.config.js')) engine = 'capacitor';
add('info', 'Project', `${engine} — ${path.basename(root)}`);

const sdkCheck = (target, min, source) => {
  if (!target) add('warn', 'Target SDK', `not found in ${source}`);
  else if (target >= REQUIRED_TARGET) add('ok', 'Target SDK', `${target} (Play requires ${REQUIRED_TARGET}+ for new apps and updates since ${REQUIRED_SINCE})`);
  else add('fail', 'Target SDK', `${target}: Play rejects new apps and updates below ${REQUIRED_TARGET} since ${REQUIRED_SINCE}`);
  if (min) add('info', 'Min SDK', `${min} (Android ${({ 21: '5.0', 22: '5.1', 23: '6', 24: '7', 25: '7.1', 26: '8', 27: '8.1', 28: '9', 29: '10', 30: '11', 31: '12', 32: '12L', 33: '13', 34: '14', 35: '15', 36: '16' })[min] || '?'}+)`);
};
const permCheck = (manifests) => {
  const perms = new Set();
  for (const m of manifests) for (const x of m.matchAll(/uses-permission[^>]*android:name="([^"]+)"/g)) perms.add(x[1].replace('android.permission.', ''));
  const sens = [...perms].filter(p => SENSITIVE[p]);
  add(sens.length ? 'warn' : 'ok', 'Permissions', perms.size ? `${[...perms].join(', ')}${sens.length ? ` — sensitive: ${sens.map(p => SENSITIVE[p]).join('; ')} (justify in Data safety / declarations, or remove)` : ''}` : 'none declared in the app manifest (plugins can add more: check the merged manifest in the APK)');
  if (manifests.some(m => /android:debuggable="true"/.test(m))) add('fail', 'Debuggable', 'android:debuggable="true" in the manifest: Play rejects debuggable release builds');
  if (manifests.some(m => /usesCleartextTraffic="true"/.test(m))) add('warn', 'Cleartext traffic', 'usesCleartextTraffic="true": allow plain HTTP only if the game really needs it');
};

if (engine === 'capacitor') {
  const vars = read('android/variables.gradle'), app = read('android/app/build.gradle') + read('android/app/build.gradle.kts');
  const num = (re, ...srcs) => { for (const s of srcs) { const m = s.match(re); if (m) return +m[1]; } return null; };
  sdkCheck(num(/targetSdkVersion\s*=?\s*(\d+)/, vars, app), num(/minSdkVersion\s*=?\s*(\d+)/, vars, app), 'android/variables.gradle');
  const vc = num(/versionCode\s*=?\s*(\d+)/, app), vn = (app.match(/versionName\s*=?\s*"([^"]+)"/) || [])[1];
  add('info', 'Version', `versionCode ${vc ?? '?'}, versionName ${vn ?? '?'} — every upload needs a higher versionCode (android/app/build.gradle)`);
  const cc = (() => { try { return JSON.parse(read('capacitor.config.json')); } catch { return {}; } })();
  const appId = cc.appId || (read('capacitor.config.ts').match(/appId:\s*['"]([^'"]+)/) || [])[1] || (app.match(/applicationId\s*=?\s*"([^"]+)"/) || [])[1];
  add(/^(com\.example|io\.ionic\.starter|com\.capacitorjs)/.test(appId || '') ? 'fail' : 'ok', 'Application ID', `${appId || '?'}${/^(com\.example|io\.ionic\.starter)/.test(appId || '') ? ' — template id: choose your own before the first upload (it can never change afterwards)' : ' (permanent after the first upload)'}`);
  permCheck([read('android/app/src/main/AndroidManifest.xml')]);
  // plugins installed but never used by the game code
  const pkg = (() => { try { return JSON.parse(read('package.json')); } catch { return {}; } })();
  const plugins = Object.keys({ ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) }).filter(d => /^@capacitor\//.test(d) && !/\/(core|android|ios|cli|assets)$/.test(d) || /^@capacitor-community\/|^capacitor-plugin-/.test(d));
  if (plugins.length) {
    const webDir = cc.webDir || 'www';
    const srcFiles = [];
    const walk = d => { let es = []; try { es = fs.readdirSync(d, { withFileTypes: true }); } catch { return; } for (const e of es) { if (['node_modules', 'android', 'ios', '.git', 'store-assets'].includes(e.name)) continue; const f = path.join(d, e.name); e.isDirectory() ? walk(f) : /\.(js|mjs|ts|tsx|jsx|html|vue|svelte)$/.test(e.name) && srcFiles.push(f); } };
    walk(path.join(root, 'src')); walk(path.join(root, webDir));
    const code = srcFiles.filter(f => !/capacitor-welcome|starter/i.test(f)).map(f => fs.readFileSync(f, 'utf8')).join('\n');
    for (const p of plugins) {
      const name = p.split('/').pop(); const cls = name.split('-').map(w => w[0].toUpperCase() + w.slice(1)).join('');
      const used = code.includes(p) || new RegExp(`\\b${cls}\\b`).test(code);
      add(used ? 'ok' : 'warn', `Plugin ${p}`, used ? 'used by the game' : 'not used by the game code: remove it (npm uninstall, then npx cap sync android) to shrink the app and simplify the Data safety form');
    }
  }
  const appName = (read('android/app/src/main/res/values/strings.xml').match(/name="app_name">([^<]+)</) || [])[1];
  if (appName) add([...appName].length > 30 ? 'warn' : 'info', 'App name (launcher)', `${appName}${[...appName].length > 12 ? ' — long names get cut under the icon on the home screen; a shorter title in strings.xml can help' : ''}`);
} else if (engine === 'unity') {
  const ps = read('ProjectSettings/ProjectSettings.asset');
  const v = re => (ps.match(re) || [])[1];
  const target = +v(/AndroidTargetSdkVersion:\s*(\d+)/), min = +v(/AndroidMinSdkVersion:\s*(\d+)/);
  if (target === 0) add('warn', 'Target SDK', `"Automatic (highest installed)": make sure Android SDK ${REQUIRED_TARGET}+ is installed in Unity, or set it explicitly (Player Settings > Other Settings > Target API Level)`);
  else sdkCheck(target, min, 'ProjectSettings.asset');
  if (target === 0 && min) sdkCheck(REQUIRED_TARGET, min, '');   // prints min only
  add('info', 'Version', `bundle version ${v(/bundleVersion:\s*(.+)/) || '?'}, version code ${v(/AndroidBundleVersionCode:\s*(\d+)/) || '?'} — every upload needs a higher version code`);
  const id = v(/applicationIdentifier:[\s\S]*?Android:\s*(\S+)/);
  add(/^com\.(DefaultCompany|Company)\b/i.test(id || '') ? 'fail' : 'ok', 'Application ID', `${id || '?'}${/DefaultCompany/i.test(id || '') ? ' — Unity default: set your own (Player Settings > Other Settings > Package Name); it can never change after the first upload' : ''}`);
  const backend = v(/scriptingBackend:[\s\S]*?Android:\s*(\d)/), arch = +v(/AndroidTargetArchitectures:\s*(\d+)/);
  add(backend === '1' ? 'ok' : 'fail', 'Scripting backend', backend === '1' ? 'IL2CPP' : 'Mono: Play requires 64-bit code, which needs IL2CPP (Player Settings > Other Settings > Scripting Backend)');
  if (!Number.isNaN(arch)) add(arch & 2 ? 'ok' : 'fail', 'Target architectures', `${['ARMv7', 'ARM64', 'x86', 'x86-64'].filter((_, i) => arch & (1 << i)).join(', ') || 'none'}${arch & 2 ? '' : ': enable ARM64, required by Google Play'}`);
  add(/androidUseCustomKeystore:\s*1/.test(ps) ? 'ok' : 'warn', 'Release keystore', /androidUseCustomKeystore:\s*1/.test(ps) ? 'custom keystore set' : 'no custom keystore: release builds must be signed with your own upload key (Publishing Settings > Keystore Manager). Back it up!');
  if (/AndroidBuildAppBundle\w*:\s*0/.test(ps) || /buildAppBundle:\s*0/.test(read('ProjectSettings/EditorBuildSettings.asset'))) add('info', 'App Bundle', 'Play requires an .aab for new apps: Build Settings > Build App Bundle (Google Play)');
  const manifests = []; const walk = d => { let es = []; try { es = fs.readdirSync(d, { withFileTypes: true }); } catch { return; } for (const e of es) { const f = path.join(d, e.name); e.isDirectory() ? walk(f) : e.name === 'AndroidManifest.xml' && manifests.push(fs.readFileSync(f, 'utf8')); } };
  walk(path.join(root, 'Assets/Plugins/Android'));
  if (manifests.length) permCheck(manifests); else add('info', 'Permissions', 'no custom manifest in Assets/Plugins/Android; check the built APK with --apk');
} else add('fail', 'Engine', 'not a Capacitor or Unity project');

// Native code in a built APK / AAB: 64-bit present and 16 KB aligned (required for apps targeting Android 15+)
if (a.apk) {
  const f = path.resolve(a.apk);
  if (!fs.existsSync(f)) add('fail', 'Build', `not found: ${f}`);
  else {
    const py = `
import sys, zipfile, struct, json
z = zipfile.ZipFile(sys.argv[1]); res = {}
for n in z.namelist():
    if not n.endswith('.so'): continue
    parts = n.split('/'); abi = parts[-2]
    b = z.read(n)
    if b[:4] != b'\\x7fELF': continue
    is64 = b[4] == 2
    if is64: phoff = struct.unpack_from('<Q', b, 0x20)[0]; phs, phn = struct.unpack_from('<HH', b, 0x36); off_al = 48; fmt = '<Q'
    else: phoff = struct.unpack_from('<I', b, 0x1c)[0]; phs, phn = struct.unpack_from('<HH', b, 0x2a); off_al = 28; fmt = '<I'
    al = [struct.unpack_from(fmt, b, phoff + i * phs + off_al)[0] for i in range(phn) if struct.unpack_from('<I', b, phoff + i * phs)[0] == 1]
    res.setdefault(abi, []).append([parts[-1], min(al) if al else 0])
print(json.dumps(res))`;
    const r = spawnSync('python3', ['-c', py, f], { encoding: 'utf8' });
    if (r.status !== 0) add('warn', 'Native code', 'could not read the build: ' + (r.stderr || '').trim().split('\n').pop());
    else {
      const libs = JSON.parse(r.stdout || '{}'), abis = Object.keys(libs);
      if (!abis.length) add('ok', 'Native code', 'none (nothing to check for 64-bit or 16 KB)');
      else {
        add(abis.includes('arm64-v8a') ? 'ok' : 'fail', '64-bit code', `ABIs: ${abis.join(', ')}${abis.includes('arm64-v8a') ? '' : ' — no arm64-v8a: Play requires 64-bit'}`);
        const bad = Object.entries(libs).filter(([abi]) => /64/.test(abi)).flatMap(([abi, l]) => l.filter(([, al]) => al < 16384).map(([n]) => `${abi}/${n}`));
        add(bad.length ? 'fail' : 'ok', '16 KB page size', bad.length ? `not 16 KB aligned: ${bad.slice(0, 6).join(', ')}${bad.length > 6 ? '…' : ''} — update the engine/plugin that ships them (Play requires 16 KB support for apps targeting Android 15+)` : `all ${Object.values(libs).flat().length} native libraries are 16 KB aligned`);
      }
      add('info', 'Build size', `${(fs.statSync(f).size / 1e6).toFixed(1)} MB (${path.basename(f)})`);
    }
  }
} else add('info', 'Native code', 'pass --apk <app.apk|.aab> to check 64-bit and 16 KB alignment of the built game');

// Report
const icon = { ok: '✓', warn: '⚠', fail: '✗', info: '•' };
for (const [st, c, d] of rows) console.log(`${icon[st]} ${c}: ${d}`);
const fails = rows.filter(r => r[0] === 'fail').length, warns = rows.filter(r => r[0] === 'warn').length;
console.log(`\n${fails ? `${fails} blocking issue(s)` : 'No blocking issues'}${warns ? `, ${warns} warning(s)` : ''}.`);
if (a.out) {
  const out = path.resolve(a.out); fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, `# Google Play publish checklist\n\nGenerated ${new Date().toISOString().slice(0, 10)} from the project (read-only).\n\n| | Check | Details |\n|---|---|---|\n${rows.map(([st, c, d]) => `| ${icon[st]} | ${c} | ${d.replace(/\|/g, '\\|')} |`).join('\n')}\n\n${fails ? `**${fails} blocking issue(s)** to fix before uploading.` : 'No blocking issues found.'}${warns ? ` ${warns} warning(s) to review.` : ''}\n\nAlso in Play Console: Data safety form, content rating questionnaire, target audience, privacy policy URL, and Play App Signing (keep your upload key backed up).\n`);
  console.log('Wrote ' + out);
}
process.exit(fails ? 1 : 0);
