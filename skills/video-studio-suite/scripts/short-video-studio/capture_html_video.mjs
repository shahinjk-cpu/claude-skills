#!/usr/bin/env node
/**
 * capture_html_video.mjs
 * 确定性 HTML / Canvas / SVG / HyperFrames 无头浏览器逐帧抓取与 FFmpeg H.264/BT.709 编码桥
 * 契约：页面就绪置位 window.READY = true，并暴露 window.seek(t, frameCenterT) 或 window.__timelines.main.seek(t)。
 * 模式：
 *   1) 单任务渲染：
 *      node capture_html_video.mjs <project_dir> [--page index.html] [--fps 30] [--dur 12] [--size 1080x1920]
 *        [--from 0 --to 6] [--blur 1 --shutter 0.5] [--query "ratio=16x9"] [--out out.mp4] [--start 0] [--frames N]
 *        [--jpeg] [--smoke-json smoke.json] [--smoke-checkpoints]
 *   2) 单浏览器实例多幕批处理：
 *      node capture_html_video.mjs --batch-json <batch_manifest.json>
 *   3) 三拍跳转纯函数校验：
 *      node capture_html_video.mjs <project_dir> --verify [--page anim_starter.html] [--samples 7] [--tol 12] [--query "ratio=16x9"]
 *   4) 静帧与场景联系表：
 *      node capture_html_video.mjs <project_dir> --stills scenes|every|boundaries [--page anim_starter.html] [--out-dir out/stills] [--step 1.0]
 *   5) 多图并排对比：
 *      node capture_html_video.mjs --compare img1.png,img2.png [--labels "A,B"] --out compare.png
 *   6) 单源双比例 4K 代码封面：
 *      node capture_html_video.mjs <project_dir> --cover-4k [--page cover_4k.html] --out-dir out --name 片名 [--guides] [--check-dir work_checks]
 */

import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const argv = process.argv.slice(2);
const opt = (key, defVal = null) => {
  const idx = argv.indexOf(`--${key}`);
  if (idx < 0) return defVal;
  const nxt = argv[idx + 1];
  if (!nxt || nxt.startsWith("--")) return true;
  return nxt;
};

const batchJsonOpt = opt("batch-json", null);
const compareOpt = opt("compare", null);
const verifyMode = Boolean(opt("verify", false));
const stillsMode = opt("stills", null);
const cover4kMode = Boolean(opt("cover-4k", false));

if (!batchJsonOpt && !compareOpt && (!argv.length || argv[0].startsWith("-"))) {
  console.error(
    "Usage:\n  node capture_html_video.mjs <project_dir> [--page index.html] [--fps 30] [--dur SEC] [--size 1080x1920] [--out out.mp4]\n" +
      "  node capture_html_video.mjs <project_dir> --verify | --stills scenes | --cover-4k --out-dir out --name 片名\n" +
      "  node capture_html_video.mjs --batch-json <batch.json> | --compare a.png,b.png --out cmp.png"
  );
  process.exit(2);
}

const MIME_MAP = {
  ".html": "text/html; charset=utf-8",
  ".htm": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".otf": "font/otf",
  ".ttf": "font/ttf",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".wav": "audio/wav",
  ".m4a": "audio/mp4",
  ".mp3": "audio/mpeg",
};

const FONT_ERR_RE = /OTS parsing error|Failed to decode downloaded font/i;

function findChromeExecutable() {
  const envPath = process.env.SVS_CHROME_PATH;
  if (envPath && fs.existsSync(envPath)) return envPath;
  const cands = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ];
  for (const c of cands) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

async function loadBrowserLib(seedDir) {
  const pkgNames = ["playwright-core", "playwright"];
  const searchDirs = [
    ...(seedDir ? [seedDir] : []),
    path.join(os.homedir(), ".short-video-studio", "node_tools"),
  ];
  for (const baseDir of searchDirs) {
    const pkgJson = path.join(baseDir, "package.json");
    const modBase = path.join(baseDir, "node_modules");
    if (!fs.existsSync(modBase)) continue;
    try {
      const req = createRequire(fs.existsSync(pkgJson) ? pkgJson : path.join(modBase, "_anchor.js"));
      for (const name of pkgNames) {
        try {
          const resolved = req.resolve(name);
          const mod = await import(pathToFileURL(resolved).href);
          return mod.default || mod;
        } catch {}
      }
    } catch {}
  }
  for (const name of pkgNames) {
    try {
      const mod = await import(name);
      return mod.default || mod;
    } catch {}
  }
  return null;
}

function startStaticServer(projectDir, defaultPage) {
  const server = http.createServer((req, res) => {
    let rawUrl = "/";
    try {
      rawUrl = decodeURIComponent((req.url || "/").split("?")[0]);
    } catch {
      res.writeHead(400);
      res.end("Bad Request");
      return;
    }
    if (rawUrl === "/favicon.ico") {
      res.writeHead(204);
      res.end();
      return;
    }
    const relPath = rawUrl === "/" ? defaultPage : rawUrl.replace(/^\/+/, "");
    const filePath = path.resolve(projectDir, relPath);
    if (
      !(filePath === projectDir || filePath.startsWith(projectDir + path.sep)) ||
      !fs.existsSync(filePath) ||
      fs.statSync(filePath).isDirectory()
    ) {
      res.writeHead(404);
      res.end("Not Found");
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME_MAP[ext] || "application/octet-stream" });
    fs.createReadStream(filePath).pipe(res);
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve({ server, port: server.address().port }));
  });
}

async function openReadyPage(browser, port, pageName, W, H, scale = 1, queryStr = "") {
  const context = await browser.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: scale,
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (err) => errors.push(`pageerror: ${String(err)}`));
  page.on("console", (msg) => {
    const txt = msg.text();
    if (msg.type() === "error" || FONT_ERR_RE.test(txt)) {
      errors.push(`console.${msg.type()}: ${txt}`);
    }
  });
  page.on("requestfailed", (req) => {
    const rUrl = req.url();
    if (rUrl.startsWith(`http://127.0.0.1:${port}`)) {
      errors.push(`requestfailed: ${rUrl} (${req.failure()?.errorText || "unknown"})`);
    }
  });
  page.on("response", (res) => {
    const rUrl = res.url();
    if (res.status() >= 400 && rUrl.startsWith(`http://127.0.0.1:${port}`) && !rUrl.endsWith("/favicon.ico")) {
      errors.push(`http ${res.status()}: ${rUrl}`);
    }
  });

  const qParts = ["render=1", String(queryStr || "").trim()].filter(Boolean);
  const targetUrl = `http://127.0.0.1:${port}/${pageName.replace(/^\/+/, "")}?${qParts.join("&")}`;
  await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(
    () => {
      const hasSeek =
        typeof window.seek === "function" ||
        (window.__timelines && window.__timelines.main && typeof window.__timelines.main.seek === "function");
      return Boolean(hasSeek && window.READY === true);
    },
    null,
    { timeout: 60000 }
  );

  const meta = await page.evaluate(() => {
    const m = window.__SVS_STAGE_META || {};
    return {
      width: Number(m.width || window.innerWidth || 1080),
      height: Number(m.height || window.innerHeight || 1920),
      fps: Number(m.fps || 30),
      duration: Number(m.duration || window.DUR || 3),
      scenes: Array.isArray(m.scenes) ? m.scenes : [],
    };
  });
  return { context, page, errors, meta };
}

async function seekPage(page, t, frameCenterT = null) {
  await page.evaluate(
    async ([curT, ft]) => {
      if (typeof window.seek === "function") {
        await window.seek(curT, ft);
      } else if (window.__timelines && window.__timelines.main) {
        window.__timelines.main.seek(curT);
      }
      const imgs = Array.from(document.querySelectorAll("img"));
      await Promise.all(imgs.map((im) => (im.complete ? Promise.resolve() : im.decode().catch(() => {}))));
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    },
    [t, frameCenterT === null ? t : frameCenterT]
  );
}

let _diffCtx = null;
let _diffPage = null;

async function diffPngBuffers(browser, bufA, bufB) {
  if (!_diffPage || _diffPage.isClosed()) {
    _diffCtx = await browser.newContext({ viewport: { width: 128, height: 128 } });
    _diffPage = await _diffCtx.newPage();
  }
  return await _diffPage.evaluate(
    async ([b64A, b64B]) => {
      const load = (s) =>
        new Promise((resolve) => {
          const im = new Image();
          im.onload = () => resolve(im);
          im.src = "data:image/png;base64," + s;
        });
      const [imA, imB] = await Promise.all([load(b64A), load(b64B)]);
      const cv = new OffscreenCanvas(imA.width, imA.height);
      const g = cv.getContext("2d", { willReadFrequently: true });
      g.drawImage(imA, 0, 0);
      const da = g.getImageData(0, 0, imA.width, imA.height).data;
      g.clearRect(0, 0, imA.width, imA.height);
      g.drawImage(imB, 0, 0);
      const db = g.getImageData(0, 0, imA.width, imA.height).data;
      let maxDiff = 0;
      let diffCount = 0;
      let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
      for (let i = 0; i < da.length; i += 4) {
        const d = Math.max(Math.abs(da[i] - db[i]), Math.abs(da[i + 1] - db[i + 1]), Math.abs(da[i + 2] - db[i + 2]));
        if (d > 0) {
          diffCount += 1;
          const px = (i / 4) % imA.width;
          const py = Math.floor(i / 4 / imA.width);
          if (px < x0) x0 = px;
          if (py < y0) y0 = py;
          if (px > x1) x1 = px;
          if (py > y1) y1 = py;
        }
        if (d > maxDiff) maxDiff = d;
      }
      return {
        maxDiff,
        diffCount,
        totalPixels: da.length / 4,
        box: diffCount > 0 ? [x0, y0, x1 - x0 + 1, y1 - y0 + 1] : null,
      };
    },
    [bufA.toString("base64"), bufB.toString("base64")]
  );
}

function measureSmokePixels(mp4File, frameCount) {
  const ffmpegBin = process.env.FFMPEG_BIN || "ffmpeg";
  const probe = spawnSync(
    ffmpegBin,
    ["-v", "error", "-i", mp4File, "-vf", "scale=64:64,format=gray", "-f", "rawvideo", "-"],
    { maxBuffer: 64 * 1024 * 1024 }
  );
  if (probe.status !== 0 || !probe.stdout || !probe.stdout.length) {
    return { nonBlackFrames: 0, meanLumas: [] };
  }
  const buf = probe.stdout;
  const pxPerFrame = 64 * 64;
  const actualFrames = Math.floor(buf.length / pxPerFrame);
  const meanLumas = [];
  let nonBlackFrames = 0;
  for (let i = 0; i < Math.min(actualFrames, frameCount); i++) {
    let sum = 0;
    const base = i * pxPerFrame;
    for (let k = 0; k < pxPerFrame; k++) sum += buf[base + k];
    const mean = sum / pxPerFrame;
    meanLumas.push(Number(mean.toFixed(2)));
    if (mean >= 4.0) nonBlackFrames += 1;
  }
  return { nonBlackFrames, meanLumas };
}

function normalizeTask(raw) {
  const projectDir = path.resolve(String(raw.projectDir || raw.project_dir));
  const pageName = String(raw.page || "index.html");
  const fps = Math.max(1, Number(raw.fps || 30) || 30);
  const sizeStr = String(raw.size || "1080x1920");
  const [W, H] = sizeStr.split("x").map((n) => Math.max(2, Number(n) || 0));
  if (W % 2 !== 0 || H % 2 !== 0) {
    throw new Error(`Width and height must be even, got ${W}x${H}`);
  }
  const outOpt = String(raw.out || path.join(projectDir, "out", "code_render.mp4"));
  const outPath = path.isAbsolute(outOpt) ? outOpt : path.resolve(process.cwd(), outOpt);
  const durOpt = raw.dur !== undefined && raw.dur !== null ? Number(raw.dur) : null;
  const fromSec = raw.from !== undefined && raw.from !== null ? Math.max(0, Number(raw.from)) : null;
  const toSec = raw.to !== undefined && raw.to !== null ? Math.max(0, Number(raw.to)) : null;
  const startFrame = Math.max(0, Number(raw.start || 0) || 0);
  const framesOpt = raw.frames !== undefined && raw.frames !== null ? Number(raw.frames) : null;
  const blurN = Math.max(1, Number(raw.blur || 1) || 1);
  const shutter = Math.max(0.1, Math.min(1.0, Number(raw.shutter || 0.5) || 0.5));
  const queryStr = String(raw.query || "");
  const useJpeg = Boolean(raw.jpeg);
  const smokeOpt = raw.smokeJson || raw.smoke_json || null;
  const smokePath = smokeOpt
    ? path.isAbsolute(String(smokeOpt))
      ? String(smokeOpt)
      : path.resolve(process.cwd(), String(smokeOpt))
    : null;
  return {
    projectDir,
    pageName,
    fps,
    W,
    H,
    outPath,
    durOpt,
    fromSec,
    toSec,
    startFrame,
    framesOpt,
    blurN,
    shutter,
    queryStr,
    useJpeg,
    smokePath,
    smokeCheckpoints: Boolean(raw.smokeCheckpoints),
  };
}

async function captureSingleTask(browser, task, chromeBin) {
  const {
    projectDir,
    pageName,
    fps,
    W,
    H,
    outPath,
    durOpt,
    fromSec,
    toSec,
    startFrame,
    framesOpt,
    blurN,
    shutter,
    queryStr,
    useJpeg,
    smokePath,
    smokeCheckpoints,
  } = task;
  const { server, port } = await startStaticServer(projectDir, pageName);
  let ff = null;
  let ffClosed = false;
  let context = null;
  let framesRendered = 0;
  let totalFrames = 0;
  let checkpoints = null;
  const errors = [];
  const tStart = Date.now();

  try {
    const opened = await openReadyPage(browser, port, pageName, W, H, 1, queryStr);
    context = opened.context;
    const page = opened.page;
    errors.push(...opened.errors);

    const effDur = Number(durOpt || opened.meta.duration || 3.0);
    const segStartFrame = fromSec !== null ? Math.round(fromSec * fps) : startFrame;
    const segEndFrame = toSec !== null ? Math.min(Math.round(effDur * fps), Math.round(toSec * fps)) : Math.round(effDur * fps);
    totalFrames = framesOpt ? Math.max(1, Number(framesOpt)) : Math.max(1, segEndFrame - segStartFrame);

    if (smokeCheckpoints) {
      const lastFrame = Math.max(0, Math.round(effDur * fps) - 1);
      checkpoints = [...new Set([0, Math.floor(lastFrame / 2), lastFrame])].map((f) => f / fps);
      totalFrames = checkpoints.length;
    }

    const ffmpegBin = process.env.FFMPEG_BIN || "ffmpeg";
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    const vfList = [];
    if (blurN > 1 && !smokeCheckpoints) {
      vfList.push(`tmix=frames=${blurN}`, `select='eq(mod(n\\,${blurN})\\,${blurN - 1})'`, `setpts=N/${fps}/TB`);
    }
    vfList.push("format=yuv420p");

    const ffArgs = [
      "-v", "error", "-y",
      "-f", "image2pipe", "-framerate", String(smokeCheckpoints ? fps : fps * blurN), "-i", "-",
      "-vf", vfList.join(","),
      "-r", String(fps),
      "-c:v", "libx264", "-preset", "medium", "-crf", "18",
      "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
      "-movflags", "+faststart", "-an",
      outPath,
    ];
    ff = spawn(ffmpegBin, ffArgs, { stdio: ["pipe", "pipe", "pipe"] });

    let ffStderr = "";
    const ffClosePromise = new Promise((res) => {
      ff.on("close", (code) => {
        ffClosed = true;
        res(code);
      });
    });
    ff.on("error", (err) => {
      ffClosed = true;
      errors.push(`ffmpeg_spawn_error: ${String(err)}`);
    });
    ff.stdin.on("error", (err) => {
      if (err && err.code !== "EPIPE") errors.push(`ffmpeg_stdin_error: ${String(err)}`);
    });
    ff.stderr.on("data", (d) => {
      ffStderr += d.toString();
    });

    const shotOpts = useJpeg ? { type: "jpeg", quality: 96, animations: "disabled" } : { type: "png", animations: "disabled" };
    const effectiveBlur = smokeCheckpoints ? 1 : blurN;
    for (let idx = 0; idx < totalFrames; idx++) {
      if (ffClosed || errors.length > 0) break;
      const frameCenterT = checkpoints ? checkpoints[idx] : (segStartFrame + idx) / fps;
      for (let sub = 0; sub < effectiveBlur; sub++) {
        const subOff = effectiveBlur > 1 ? ((sub + 0.5) / effectiveBlur - 0.5) * (shutter / fps) : 0;
        const subT = Math.max(0, Math.min(effDur, frameCenterT + subOff));
        await seekPage(page, subT, frameCenterT);
        if (ffClosed) break;
        const buf = await page.screenshot(shotOpts);
        if (ffClosed) break;
        if (!ff.stdin.write(buf)) {
          await new Promise((res) => {
            const onDrain = () => { ff.off("close", onClose); res(); };
            const onClose = () => { ff.stdin.off("drain", onDrain); res(); };
            ff.stdin.once("drain", onDrain);
            ff.once("close", onClose);
          });
        }
      }
      framesRendered += 1;
      if (opened.errors.length > 0) errors.push(...opened.errors.splice(0));
    }

    if (!ffClosed && ff.stdin.writable) ff.stdin.end();
    const ffExit = await ffClosePromise;
    if (ffExit !== 0) errors.push(`ffmpeg exit=${ffExit}: ${ffStderr.slice(-400)}`);
  } catch (exc) {
    errors.push(`capture_exception: ${String(exc)}`);
  } finally {
    if (ff && !ffClosed) {
      try { ff.stdin.destroy(); } catch {}
      try { ff.kill("SIGKILL"); } catch {}
    }
    if (context) await context.close().catch(() => {});
    server.close();
  }

  const elapsedMs = Date.now() - tStart;
  const avgMsPerFrame = framesRendered > 0 ? Number((elapsedMs / framesRendered).toFixed(1)) : 0;

  if (smokePath) {
    const pxRes = fs.existsSync(outPath) ? measureSmokePixels(outPath, framesRendered) : { nonBlackFrames: 0, meanLumas: [] };
    const smokeReport = {
      ok: errors.length === 0 && framesRendered === totalFrames && totalFrames > 0 && pxRes.nonBlackFrames === totalFrames,
      frames_rendered: framesRendered,
      expected_frames: totalFrames,
      non_black_frames: pxRes.nonBlackFrames,
      mean_lumas: pxRes.meanLumas,
      avg_ms_per_frame: avgMsPerFrame,
      checkpoints_sec: checkpoints,
      chrome_executable: chromeBin,
      errors,
    };
    fs.mkdirSync(path.dirname(smokePath), { recursive: true });
    fs.writeFileSync(smokePath, JSON.stringify(smokeReport, null, 2), "utf-8");
  }
  return { ok: errors.length === 0 && framesRendered === totalFrames && totalFrames > 0, framesRendered, totalFrames, avgMsPerFrame, outPath, errors };
}

async function runVerifyPureFunction(browser, projectDir, pageName, W, H, queryStr, samples = 7, tol = 12) {
  const { server, port } = await startStaticServer(projectDir, pageName);
  let context = null;
  try {
    const opened = await openReadyPage(browser, port, pageName, W, H, 0.5, queryStr);
    context = opened.context;
    const { page, meta, errors } = opened;
    const dur = Math.max(1.0, meta.duration);
    const ts = Array.from({ length: samples }, (_, i) => Number((((i + 0.5) / samples) * dur).toFixed(4)));
    for (const sc of meta.scenes || []) {
      if (typeof sc.start === "number") ts.push(Number(Math.min(dur - 0.01, sc.start + 0.001).toFixed(4)));
    }
    const checks = [];
    let failed = 0;
    for (const t of [...new Set(ts)]) {
      await seekPage(page, t, t);
      const a1 = await page.screenshot({ type: "png", animations: "disabled" });
      await seekPage(page, t, t);
      const a2 = await page.screenshot({ type: "png", animations: "disabled" });
      const jumpT = Number(((t + dur * 0.5) % dur).toFixed(4));
      await seekPage(page, jumpT, jumpT);
      await page.screenshot({ type: "png", animations: "disabled" });
      await seekPage(page, t, t);
      const a3 = await page.screenshot({ type: "png", animations: "disabled" });

      const d12 = await diffPngBuffers(browser, a1, a2);
      const d13 = await diffPngBuffers(browser, a1, a3);
      const worst = d12.maxDiff >= d13.maxDiff ? d12 : d13;
      const ok = worst.maxDiff <= tol;
      if (!ok) failed += 1;
      const diagnosis =
        ok
          ? "pure_ok"
          : d12.diffCount === 0 && d13.diffCount > 0
          ? "state_leak_after_jump"
          : "nondeterministic_or_jitter";
      checks.push({ t_sec: t, ok, max_diff: worst.maxDiff, diff_pixels: worst.diffCount, box: worst.box, diagnosis });
    }
    const safeAlerts = await page.evaluate(() => [...new Set(window.__SVS_SAFE_ALERTS || [])]);
    if (errors.length > 0) failed += 1;
    const report = { ok: failed === 0, tol, samples: checks.length, checks, safe_alerts: safeAlerts, errors };
    console.log(JSON.stringify(report, null, 2));
    return report.ok;
  } finally {
    if (context) await context.close().catch(() => {});
    server.close();
  }
}

async function runStillsSheet(browser, projectDir, pageName, W, H, queryStr, mode, outDir, stepSec = 1.0) {
  const { server, port } = await startStaticServer(projectDir, pageName);
  let context = null;
  try {
    fs.mkdirSync(outDir, { recursive: true });
    const opened = await openReadyPage(browser, port, pageName, W, H, 0.5, queryStr);
    context = opened.context;
    const { page, meta, errors } = opened;
    const dur = Math.max(0.5, meta.duration);
    const fps = meta.fps || 30;
    const times = [];
    if (mode === "scenes" && meta.scenes.length) {
      for (const s of meta.scenes) times.push([(s.start + s.end) * 0.5, s.label || s.id]);
    } else if (mode === "boundaries" && meta.scenes.length) {
      for (const s of meta.scenes) {
        if (s.start > 0.05) {
          for (const d of [-2, -1, 0, 1, 2]) times.push([Math.max(0, Math.min(dur - 0.01, s.start + d / fps)), `${s.id} ${d >= 0 ? "+" : ""}${d}f`]);
        }
      }
    } else {
      const st = Math.max(0.25, Number(stepSec) || 1.0);
      for (let t = 0; t < dur; t += st) times.push([Number(t.toFixed(3)), `${t.toFixed(2)}s`]);
    }

    const items = [];
    for (const [t, label] of times) {
      const tt = Math.max(0, Math.min(dur - 0.001, t));
      await seekPage(page, tt, tt);
      const fp = path.join(outDir, `still_${tt.toFixed(3).replace(".", "_")}s.png`);
      const buf = await page.screenshot({ type: "png", animations: "disabled" });
      fs.writeFileSync(fp, buf);
      items.push({ t: tt, label, file: fp, b64: buf.toString("base64") });
    }

    let sheetPath = null;
    if (items.length > 1) {
      const cols = Math.min(W < H ? 6 : 5, items.length);
      const tw = W < H ? 240 : 384;
      const th = Math.round((tw * H) / W);
      const sCtx = await browser.newContext({ viewport: { width: cols * (tw + 8) + 8, height: 400 } });
      const sPage = await sCtx.newPage();
      await sPage.setContent(
        `<html><body style="margin:0;background:#0a0b0f;padding:8px;display:grid;grid-template-columns:repeat(${cols},${tw}px);gap:8px;font:12px ui-monospace,Menlo,monospace;color:#cbd5e1;">` +
          items
            .map(
              (it) =>
                `<div><img src="data:image/png;base64,${it.b64}" style="width:${tw}px;height:${th}px;display:block;outline:1px solid #222;" />` +
                `<div style="padding:4px 2px;">${it.t.toFixed(2)}s · ${it.label}</div></div>`
            )
            .join("") +
          "</body></html>"
      );
      await sPage.waitForLoadState("load");
      sheetPath = path.join(outDir, `sheet_${mode}.png`);
      await sPage.screenshot({ path: sheetPath, fullPage: true });
      await sCtx.close();
    }
    console.log(JSON.stringify({ ok: errors.length === 0, count: items.length, sheet: sheetPath, errors }, null, 2));
    return errors.length === 0;
  } finally {
    if (context) await context.close().catch(() => {});
    server.close();
  }
}

async function runCompareImages(browser, csvPaths, labelsCsv, outPath) {
  const paths = String(csvPaths).split(",").map((s) => path.resolve(s.trim())).filter(Boolean);
  const labels = String(labelsCsv || "").split(",");
  const tileW = paths.length > 3 ? 420 : 640;
  const items = paths.map((p, idx) => ({
    b64: fs.readFileSync(p).toString("base64"),
    label: (labels[idx] || path.basename(p)).trim(),
  }));
  const ctx = await browser.newContext({ viewport: { width: items.length * (tileW + 12) + 12, height: 320 } });
  const page = await ctx.newPage();
  await page.setContent(
    `<html><body style="margin:0;background:#0a0b0f;padding:12px;display:flex;gap:12px;align-items:flex-start;font:14px system-ui,sans-serif;color:#e2e8f0;">` +
      items
        .map(
          (it) =>
            `<div style="width:${tileW}px;"><img src="data:image/png;base64,${it.b64}" style="width:${tileW}px;display:block;outline:1px solid #262936;" />` +
            `<div style="padding:6px 2px;">${it.label}</div></div>`
        )
        .join("") +
      "</body></html>"
  );
  await page.waitForLoadState("load");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await page.screenshot({ path: outPath, fullPage: true });
  await ctx.close();
  console.log(JSON.stringify({ ok: true, out: outPath, compared: paths.length }, null, 2));
  return true;
}

async function runCover4k(browser, projectDir, pageName, outDir, baseName, withGuides, checkDir) {
  const { server, port } = await startStaticServer(projectDir, pageName);
  fs.mkdirSync(outDir, { recursive: true });
  if (withGuides) fs.mkdirSync(checkDir, { recursive: true });
  const outputs = [];
  const allErrors = [];
  try {
    const specs = [
      { key: "16x9", W: 1920, H: 1080, suffix: "land_4k" },
      { key: "3x4", W: 1080, H: 1440, suffix: "port_4k" },
    ];
    for (const sp of specs) {
      const jobs = [{ q: `ratio=${sp.key}`, dest: path.join(outDir, `${baseName}_${sp.suffix}.png`), isGuide: false }];
      if (withGuides) {
        jobs.push({ q: `ratio=${sp.key}&guides=1`, dest: path.join(checkDir, `${baseName}_${sp.suffix}_safe_check.png`), isGuide: true });
      }
      for (const jb of jobs) {
        const opened = await openReadyPage(browser, port, pageName, sp.W, sp.H, 2, jb.q);
        await seekPage(opened.page, 0, 0);
        const buf = await opened.page.screenshot({ type: "png", animations: "disabled" });
        fs.writeFileSync(jb.dest, buf);
        allErrors.push(...opened.errors);
        await opened.context.close();
        outputs.push({
          ratio: sp.key,
          width: sp.W * 2,
          height: sp.H * 2,
          is_guide: jb.isGuide,
          path: jb.dest,
        });
      }
    }
    const ok = allErrors.length === 0;
    console.log(JSON.stringify({ ok, outputs, errors: allErrors }, null, 2));
    return ok;
  } finally {
    server.close();
  }
}

const seedDir = compareOpt ? process.cwd() : batchJsonOpt ? path.dirname(path.resolve(String(batchJsonOpt))) : path.resolve(argv[0]);
const pw = await loadBrowserLib(seedDir);
if (!pw || !pw.chromium) {
  console.error("[capture_html] 未安装 playwright-core/playwright。请运行 `python3 scripts/check_and_setup.py --init-browser`。");
  process.exit(3);
}

const chromeBin = findChromeExecutable();
const commonArgs = ["--ignore-gpu-blocklist", "--no-sandbox", "--font-render-hinting=none", "--disable-lcd-text"];
const gpuLaunchOpts = { headless: true, args: commonArgs };
const swLaunchOpts = {
  headless: true,
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", ...commonArgs],
};
if (chromeBin) {
  gpuLaunchOpts.executablePath = chromeBin;
  swLaunchOpts.executablePath = chromeBin;
}

let browser = null;
try {
  try {
    browser = await pw.chromium.launch(gpuLaunchOpts);
  } catch {
    browser = await pw.chromium.launch(swLaunchOpts);
  }

  if (compareOpt) {
    const outP = path.resolve(String(opt("out", "compare.png")));
    const ok = await runCompareImages(browser, compareOpt, opt("labels", ""), outP);
    process.exit(ok ? 0 : 1);
  }

  if (cover4kMode) {
    const pDir = path.resolve(argv[0]);
    const pageName = String(opt("page", "cover_4k.html"));
    const outDir = path.resolve(String(opt("out-dir", path.join(pDir, "out"))));
    const baseName = String(opt("name", "09_cover"));
    const withGuides = Boolean(opt("guides", false));
    const checkDir = path.resolve(String(opt("check-dir", path.join(outDir, "work_checks"))));
    const ok = await runCover4k(browser, pDir, pageName, outDir, baseName, withGuides, checkDir);
    process.exit(ok ? 0 : 1);
  }

  if (verifyMode) {
    const pDir = path.resolve(argv[0]);
    const pageName = String(opt("page", "anim_starter.html"));
    const [W, H] = String(opt("size", "1920x1080")).split("x").map(Number);
    const ok = await runVerifyPureFunction(
      browser,
      pDir,
      pageName,
      W,
      H,
      String(opt("query", "")),
      Number(opt("samples", 7)),
      Number(opt("tol", 12))
    );
    process.exit(ok ? 0 : 1);
  }

  if (stillsMode) {
    const pDir = path.resolve(argv[0]);
    const pageName = String(opt("page", "anim_starter.html"));
    const [W, H] = String(opt("size", "1920x1080")).split("x").map(Number);
    const outDir = path.resolve(String(opt("out-dir", path.join(pDir, "out", "stills"))));
    const ok = await runStillsSheet(
      browser,
      pDir,
      pageName,
      W,
      H,
      String(opt("query", "")),
      String(stillsMode),
      outDir,
      Number(opt("step", 1.0))
    );
    process.exit(ok ? 0 : 1);
  }

  let tasks = [];
  if (batchJsonOpt) {
    const bPath = path.isAbsolute(String(batchJsonOpt)) ? String(batchJsonOpt) : path.resolve(process.cwd(), String(batchJsonOpt));
    const rawJson = JSON.parse(fs.readFileSync(bPath, "utf-8"));
    const arr = Array.isArray(rawJson) ? rawJson : rawJson.tasks || [];
    tasks = arr.map(normalizeTask);
  } else {
    tasks = [
      normalizeTask({
        projectDir: argv[0],
        page: opt("page", "index.html"),
        fps: opt("fps", 30),
        size: opt("size", "1080x1920"),
        out: opt("out", path.join(path.resolve(argv[0]), "out", "code_render.mp4")),
        dur: opt("dur", null),
        from: opt("from", null),
        to: opt("to", null),
        start: opt("start", 0),
        frames: opt("frames", null),
        blur: opt("blur", 1),
        shutter: opt("shutter", 0.5),
        query: opt("query", ""),
        jpeg: Boolean(opt("jpeg", false)),
        smokeJson: opt("smoke-json", null),
        smokeCheckpoints: Boolean(opt("smoke-checkpoints", false)),
      }),
    ];
  }

  if (!tasks.length) {
    console.error("[capture_html] Empty task list");
    process.exit(2);
  }

  const results = [];
  const concurrency = Math.min(2, tasks.length);
  let cursor = 0;
  async function worker() {
    while (cursor < tasks.length) {
      const myIdx = cursor++;
      results[myIdx] = await captureSingleTask(browser, tasks[myIdx], chromeBin);
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));

  const failed = results.filter((r) => !r || !r.ok);
  if (failed.length > 0) {
    const f0 = failed[0];
    console.error(`[capture_html] FAILED: frames=${f0.framesRendered}/${f0.totalFrames}, errors=${JSON.stringify(f0.errors)}`);
    process.exit(1);
  }
  for (const r of results) {
    console.log(`[capture_html] OK: ${r.framesRendered} frames (${r.avgMsPerFrame} ms/f) -> ${r.outPath}`);
  }
} finally {
  if (browser) await browser.close().catch(() => {});
}
