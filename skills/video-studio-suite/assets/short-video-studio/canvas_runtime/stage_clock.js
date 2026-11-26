/* stage_clock.js — 零依赖确定性舞台时钟与纯函数动效运行时 (window.SVSStage)
 * 核心原则：任意时刻画面完全由 render(t) 决定，支持 t（子帧）与 frameT（帧中心）双时钟防模糊重影。
 */
(function () {
  "use strict";

  const S = {};
  S.TAU = Math.PI * 2;
  S.frameT = 0;

  // ── 数值与插值 ───────────────────────────────────────────
  S.clamp = (x, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, x));
  S.lerp = (a, b, p) => a + (b - a) * p;
  S.invLerp = (a, b, x) => (b === a ? 0 : (x - a) / (b - a));
  S.prog = (t, t0, t1, easeFn) => {
    const u = S.clamp(S.invLerp(t0, t1, t));
    return easeFn ? easeFn(u) : u;
  };
  S.map = (t, t0, t1, v0, v1, easeFn) => S.lerp(v0, v1, S.prog(t, t0, t1, easeFn));
  S.smoothstep = (a, b, x) => {
    const u = S.clamp(S.invLerp(a, b, x));
    return u * u * (3 - 2 * u);
  };
  S.step = (t, fps = 12) => Math.floor(t * fps + 1e-6) / fps;

  // ── 缓动白名单 ───────────────────────────────────────────
  const E = {
    linear: (u) => u,
    inQuad: (u) => u * u,
    outQuad: (u) => 1 - (1 - u) * (1 - u),
    inOutQuad: (u) => (u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2),
    inCubic: (u) => u * u * u,
    outCubic: (u) => 1 - Math.pow(1 - u, 3),
    inOutCubic: (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2),
    outQuart: (u) => 1 - Math.pow(1 - u, 4),
    inOutQuart: (u) => (u < 0.5 ? 8 * Math.pow(u, 4) : 1 - Math.pow(-2 * u + 2, 4) / 2),
    inQuint: (u) => Math.pow(u, 5),
    outQuint: (u) => 1 - Math.pow(1 - u, 5),
    inOutQuint: (u) => (u < 0.5 ? 16 * Math.pow(u, 5) : 1 - Math.pow(-2 * u + 2, 5) / 2),
    inExpo: (u) => (u <= 0 ? 0 : Math.pow(2, 10 * u - 10)),
    outExpo: (u) => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * u)),
    inOutExpo: (u) =>
      u <= 0 ? 0 : u >= 1 ? 1 : u < 0.5 ? Math.pow(2, 20 * u - 10) / 2 : (2 - Math.pow(2, -20 * u + 10)) / 2,
    inOutSine: (u) => -(Math.cos(Math.PI * u) - 1) / 2,
    outBack: (u, s = 1.70158) => 1 + (s + 1) * Math.pow(u - 1, 3) + s * Math.pow(u - 1, 2),
    outElastic: (u) =>
      u <= 0 ? 0 : u >= 1 ? 1 : Math.pow(2, -10 * u) * Math.sin((u * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1,
    bezier: (x1, y1, x2, y2) => {
      const cx = 3 * x1;
      const bx = 3 * (x2 - x1) - cx;
      const ax = 1 - cx - bx;
      const cy = 3 * y1;
      const by = 3 * (y2 - y1) - cy;
      const ay = 1 - cy - by;
      const sx = (u) => ((ax * u + bx) * u + cx) * u;
      const sy = (u) => ((ay * u + by) * u + cy) * u;
      const dx = (u) => (3 * ax * u + 2 * bx) * u + cx;
      return (x) => {
        if (x <= 0) return 0;
        if (x >= 1) return 1;
        let u = x;
        for (let i = 0; i < 8; i++) {
          const d = dx(u);
          if (Math.abs(d) < 1e-6) break;
          u -= (sx(u) - x) / d;
        }
        return sy(S.clamp(u));
      };
    },
  };
  S.ease = E;

  // ── 关键帧与对数缩放 ──────────────────────────────────────
  S.kf = (t, keys, defaultEase = E.inOutCubic) => {
    if (!keys || !keys.length) return 0;
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [t1, v1, easeFn] = keys[i];
      if (t <= t1) {
        const [t0, v0] = keys[i - 1];
        const p = (easeFn || defaultEase)(S.clamp(S.invLerp(t0, t1, t)));
        return Array.isArray(v0) ? v0.map((a, idx) => S.lerp(a, v1[idx], p)) : S.lerp(v0, v1, p);
      }
    }
    return keys[keys.length - 1][1];
  };

  S.kfZoom = (t, keys, defaultEase = E.inOutCubic) =>
    Math.exp(
      S.kf(
        t,
        keys.map(([tt, zz, ee]) => [tt, Math.log(Math.max(1e-4, zz)), ee]),
        defaultEase
      )
    );

  // ── 闭式解析阻尼弹簧 ──────────────────────────────────────
  S.springUnit = (dt, stiffness = 170, damping = 26, mass = 1, v0 = 0) => {
    if (dt <= 0) return 0;
    const w0 = Math.sqrt(stiffness / mass);
    const zeta = damping / (2 * Math.sqrt(stiffness * mass));
    if (zeta < 1) {
      const wd = w0 * Math.sqrt(1 - zeta * zeta);
      const b = (zeta * w0 - v0) / wd;
      return 1 - Math.exp(-zeta * w0 * dt) * (Math.cos(wd * dt) + b * Math.sin(wd * dt));
    }
    return 1 - Math.exp(-w0 * dt) * (1 + (w0 - v0) * dt);
  };

  S.spring = (t, t0, from, to, stiffness = 170, damping = 26, mass = 1) =>
    S.lerp(from, to, S.springUnit(t - t0, stiffness, damping, mass));

  S.springTrack = (t, targets, stiffness = 170, damping = 26, mass = 1) => {
    if (!targets || !targets.length) return 0;
    let val = targets[0][1];
    for (let i = 1; i < targets.length; i++) {
      const [ti, vi] = targets[i];
      if (t < ti) break;
      val += (vi - targets[i - 1][1]) * S.springUnit(t - ti, stiffness, damping, mass);
    }
    return val;
  };

  // ── 入出场包络与节奏编排 ──────────────────────────────────
  S.envelope = (t, inA, inB, outA = Infinity, outB = Infinity, inEase = E.outCubic, outEase = E.inCubic) =>
    Math.min(S.prog(t, inA, inB, inEase), 1 - S.prog(t, outA, outB, outEase));

  S.stagger = (idx, total, spread, easeFn = E.linear) =>
    total <= 1 ? 0 : easeFn(idx / (total - 1)) * spread;

  S.impulse = (t, hitTimes, decay = 0.18) => {
    let v = 0;
    for (const h of hitTimes) {
      const d = t - h;
      if (d >= 0 && d < decay * 8) v = Math.max(v, Math.exp(-d / decay));
    }
    return v;
  };

  // ── 确定性伪随机与值噪声 ──────────────────────────────────
  S.rng = (seed = 1) => {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) | 0;
      let r = Math.imul(a ^ (a >>> 15), 1 | a);
      r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  };

  S.hash = (i, seed = 0) => {
    let h = (Math.imul(i | 0, 374761393) + Math.imul(seed | 0, 668265263)) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  };

  const fade5 = (u) => u * u * u * (u * (u * 6 - 15) + 10);

  S.noise2 = (x, y, seed = 0) => {
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const xf = x - xi;
    const yf = y - yi;
    const h = (a, b) => S.hash((a * 73856093) ^ (b * 19349663), seed);
    const u = fade5(xf);
    const v = fade5(yf);
    return S.lerp(S.lerp(h(xi, yi), h(xi + 1, yi), u), S.lerp(h(xi, yi + 1), h(xi + 1, yi + 1), u), v) * 2 - 1;
  };

  S.fbm = (x, y, octaves = 4, seed = 0) => {
    let sum = 0;
    let amp = 0.5;
    let freq = 1;
    for (let i = 0; i < octaves; i++) {
      sum += amp * S.noise2(x * freq, y * freq, seed + i * 19);
      freq *= 2;
      amp *= 0.5;
    }
    return sum;
  };

  // ── 线性光空间混色（防 sRGB 直接插值发灰） ──────────────────
  S.hexToRgb = (hex) => {
    let h = String(hex || "#ffffff").replace("#", "").trim();
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    const n = parseInt(h, 16);
    if (Number.isNaN(n)) return [255, 255, 255];
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };

  S.rgba = (col, alpha = 1) => {
    const [r, g, b] = typeof col === "string" ? S.hexToRgb(col) : col;
    return `rgba(${r | 0},${g | 0},${b | 0},${S.clamp(alpha, 0, 1)})`;
  };

  S.mixLinearColor = (c1, c2, p) => {
    const a = typeof c1 === "string" ? S.hexToRgb(c1) : c1;
    const b = typeof c2 === "string" ? S.hexToRgb(c2) : c2;
    const toLin = (v) => Math.pow(S.clamp(v / 255, 0, 1), 2.2);
    const toSrgb = (v) => Math.round(255 * Math.pow(S.clamp(v, 0, 1), 1 / 2.2));
    return a.map((x, idx) => toSrgb(S.lerp(toLin(x), toLin(b[idx]), S.clamp(p, 0, 1))));
  };

  // ── CPU 锁定确定性 Canvas 工厂 ─────────────────────────────
  S.createCanvas = (parent, w, h, dpr = window.devicePixelRatio || 1) => {
    const el = document.createElement("canvas");
    el.width = Math.max(1, Math.round(w * dpr));
    el.height = Math.max(1, Math.round(h * dpr));
    el.style.cssText = `position:absolute;left:0;top:0;width:${w}px;height:${h}px;`;
    parent.appendChild(el);
    const ctx = el.getContext("2d", { willReadFrequently: true });
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return {
      el,
      ctx,
      clear() {
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, el.width, el.height);
        ctx.restore();
      },
    };
  };

  // ── 异步资源等待队列 ──────────────────────────────────────
  const waitQueue = [];
  S.wait = (promise) => {
    waitQueue.push(promise);
    return promise;
  };
  S.loadImage = (src) =>
    S.wait(
      new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = (err) => reject(err);
        img.src = src;
      })
    );

  // ── 舞台注册与本地交互预览器 ────────────────────────────────
  function mountPreviewBar(meta, seekFn) {
    const bar = document.createElement("div");
    bar.style.cssText =
      "position:fixed;left:16px;right:16px;bottom:14px;z-index:9999;background:rgba(10,14,22,0.88);" +
      "border:1px solid rgba(255,255,255,0.16);border-radius:12px;padding:8px 14px;display:flex;" +
      "align-items:center;gap:12px;color:#e2e8f0;font:13px ui-monospace,Menlo,monospace;";
    const btn = document.createElement("button");
    btn.textContent = "播放";
    btn.style.cssText =
      "background:#38bdf8;color:#06111c;border:0;border-radius:6px;padding:4px 10px;font-weight:700;cursor:pointer;";
    const range = document.createElement("input");
    range.type = "range";
    range.min = "0";
    range.max = String(meta.duration);
    range.step = String(1 / meta.fps);
    range.value = "0";
    range.style.flex = "1";
    const info = document.createElement("span");
    info.textContent = `0.00s / ${meta.duration.toFixed(2)}s`;
    bar.append(btn, range, info);
    document.body.appendChild(bar);

    let playing = false;
    let curT = 0;
    let lastTs = 0;
    const drawAt = async (t) => {
      curT = S.clamp(t, 0, Math.max(0, meta.duration - 1 / meta.fps));
      range.value = String(curT);
      info.textContent = `${curT.toFixed(2)}s / ${meta.duration.toFixed(2)}s`;
      await seekFn(curT, curT);
    };
    const tick = (ts) => {
      if (!playing) return;
      if (!lastTs) lastTs = ts;
      const dt = (ts - lastTs) / 1000;
      lastTs = ts;
      const nxt = curT + dt;
      if (nxt >= meta.duration) {
        drawAt(0);
      } else {
        drawAt(nxt);
      }
      requestAnimationFrame(tick);
    };
    btn.onclick = () => {
      playing = !playing;
      btn.textContent = playing ? "暂停" : "播放";
      lastTs = 0;
      if (playing) requestAnimationFrame(tick);
    };
    range.oninput = () => {
      playing = false;
      btn.textContent = "播放";
      drawAt(Number(range.value));
    };
    window.addEventListener("keydown", (ev) => {
      if (ev.code === "Space") {
        ev.preventDefault();
        btn.click();
      } else if (ev.code === "ArrowRight") {
        playing = false;
        btn.textContent = "播放";
        drawAt(curT + (ev.shiftKey ? 1 : 1 / meta.fps));
      } else if (ev.code === "ArrowLeft") {
        playing = false;
        btn.textContent = "播放";
        drawAt(curT - (ev.shiftKey ? 1 : 1 / meta.fps));
      }
    });
  }

  S.mount = (cfg) => {
    const width = Number(cfg.width || 1920);
    const height = Number(cfg.height || 1080);
    const fps = Number(cfg.fps || 30);
    const duration = Number(cfg.duration || 10);
    const stage = cfg.stage || document.getElementById("stage");
    const scenes = cfg.scenes || [];
    const cues = cfg.cues || [];
    const isHeadless = Boolean(navigator.webdriver || /[?&]render=1/.test(location.search));

    stage.style.width = `${width}px`;
    stage.style.height = `${height}px`;
    stage.style.position = "absolute";
    stage.style.left = "0";
    stage.style.top = "0";
    stage.style.overflow = "hidden";
    stage.style.transformOrigin = "0 0";

    window.DUR = duration;
    window.READY = false;
    window.__SVS_STAGE_META = { width, height, fps, duration, scenes, cues };
    window.__SVS_SAFE_ALERTS = [];

    window.seek = async (t, frameCenterT) => {
      const clampedT = S.clamp(Number(t) || 0, 0, Math.max(0, duration));
      S.frameT = frameCenterT === undefined || frameCenterT === null ? clampedT : Number(frameCenterT);
      await cfg.render(clampedT);
    };

    const boot = (async () => {
      if (document.fonts) {
        const loads = [...document.fonts].map((ff) => ff.load().catch(() => null));
        await Promise.all(loads);
        await document.fonts.ready;
      }
      await Promise.all(waitQueue);
      await window.seek(0, 0);
      window.READY = true;
    })();
    window.__SVS_READY_PROMISE = boot;

    if (!isHeadless) {
      boot.then(() => {
        const fit = () => {
          const sc = Math.min((window.innerWidth - 24) / width, (window.innerHeight - 76) / height, 1);
          stage.style.transform = `translate(${Math.max(12, (window.innerWidth - width * sc) / 2)}px, 12px) scale(${sc})`;
        };
        fit();
        window.addEventListener("resize", fit);
        mountPreviewBar(window.__SVS_STAGE_META, window.seek);
      });
    }
    return boot;
  };

  window.SVSStage = S;
})();
