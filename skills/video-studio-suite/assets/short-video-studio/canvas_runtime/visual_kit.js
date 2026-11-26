/* visual_kit.js — 六层有序视觉画板与低成本伪物理 Bloom 套件 (window.SVSVisualKit)
 * 依赖 stage_clock.js (window.SVSStage)。全部原语均为 t 的纯函数。
 */
(function () {
  "use strict";

  function createVisualKit(opts) {
    const S = window.SVSStage;
    const W = Number(opts.width || 1920);
    const H = Number(opts.height || 1080);
    const stage = opts.stage || document.getElementById("stage");
    const seed = Number(opts.seed || 17);
    const fontSans = opts.fontSans || "SVSSans, PingFang SC, Microsoft YaHei, sans-serif";
    const fontSerif = opts.fontSerif || "SVSSerif, Songti SC, Noto Serif CJK SC, serif";
    const palette = Object.assign(
      {
        bg: "#05070d",
        ink: "#f1f5f9",
        sub: "#94a3b8",
        accent: "#5ce1e6",
        accent2: "#f59e0b",
        alert: "#fb7185",
      },
      opts.palette || {}
    );

    const K = { W, H, P: palette, fontSans, fontSerif };
    K.rgba = (c, a = 1) => S.rgba(c, a);
    K.mix = (c1, c2, p) => S.mixLinearColor(c1, c2, p);
    K.accentA = (a) => S.rgba(palette.accent, a);
    K.inkA = (a) => S.rgba(palette.ink, a);

    // ── 分层舞台：bg(1) -> bg2(2) -> main(4) + bloom(4,screen) -> world(5) -> fg(6,screen) -> hud(8) -> caption(9) -> flash(10) -> vignette(11) -> grain(12)
    stage.style.background = palette.bg;
    const mkCanvasLayer = (name, z, dpr) => {
      const c = S.createCanvas(stage, W, H, dpr);
      c.el.style.zIndex = String(z);
      c.el.dataset.layer = name;
      return c;
    };
    const mkDomLayer = (z, extraCss) => {
      const d = document.createElement("div");
      Object.assign(
        d.style,
        {
          position: "absolute",
          left: "0",
          top: "0",
          width: `${W}px`,
          height: `${H}px`,
          pointerEvents: "none",
          zIndex: String(z),
        },
        extraCss || {}
      );
      stage.appendChild(d);
      return d;
    };

    const layers = {
      bg: mkCanvasLayer("bg", 1, 1),
      bg2: mkCanvasLayer("bg2", 2, 1),
      main: mkCanvasLayer("main", 4, 1),
      bloom: mkCanvasLayer("bloom", 4, 0.5),
      fg: mkCanvasLayer("fg", 6, 1),
    };
    layers.bloom.el.style.mixBlendMode = "screen";
    layers.fg.el.style.mixBlendMode = "screen";

    K.world = document.getElementById("world") || mkDomLayer(5, { transformOrigin: "0 0" });
    K.world.style.zIndex = "5";
    K.hudLayer = mkDomLayer(8);
    K.captionLayer = mkDomLayer(9);
    const flashLayer = mkDomLayer(10, { background: opts.flashColor || "#ffffff", opacity: "0", mixBlendMode: "screen" });
    mkDomLayer(11, {
      background: `radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 52%, rgba(0,0,0,${opts.vignette ?? 0.54}) 100%)`,
    });
    const grainCanvas = mkCanvasLayer("grain", 12, 0.5);
    grainCanvas.el.style.mixBlendMode = "overlay";
    grainCanvas.el.style.opacity = String(opts.grain ?? 0.16);

    K.ctx = layers.main.ctx;
    K.bgCtx = layers.bg.ctx;
    K.bg2Ctx = layers.bg2.ctx;
    K.fgCtx = layers.fg.ctx;

    // ── 1/4 分辨率高光阈值 Bloom 离屏缓冲区 ────────────────────
    const bloomStrength = opts.bloom ?? 0.85;
    const bW = Math.max(64, Math.round(W / 4));
    const bH = Math.max(64, Math.round(H / 4));
    const bThresh = document.createElement("canvas");
    bThresh.width = bW;
    bThresh.height = bH;
    const bThreshCtx = bThresh.getContext("2d", { willReadFrequently: true });
    const bBlur = document.createElement("canvas");
    bBlur.width = bW;
    bBlur.height = bH;
    const bBlurCtx = bBlur.getContext("2d", { willReadFrequently: true });

    // ── 发光精灵缓存（加载期预烘焙，替代昂贵 shadowBlur） ────────
    function buildGlowSprite(r, stops) {
      const c = document.createElement("canvas");
      c.width = r * 2;
      c.height = r * 2;
      const g = c.getContext("2d", { willReadFrequently: true });
      const grad = g.createRadialGradient(r, r, 0, r, r, r);
      for (const [pos, col] of stops) grad.addColorStop(pos, col);
      g.fillStyle = grad;
      g.fillRect(0, 0, r * 2, r * 2);
      return c;
    }

    const spritePool = new Map();
    K.getGlowSprite = (hexColor, kind = "core") => {
      const key = `${hexColor}:${kind}`;
      if (spritePool.has(key)) return spritePool.get(key);
      const rgbStr = S.hexToRgb(hexColor).join(",");
      const spr =
        kind === "soft"
          ? buildGlowSprite(64, [
              [0, `rgba(${rgbStr},0.50)`],
              [0.48, `rgba(${rgbStr},0.14)`],
              [1, `rgba(${rgbStr},0)`],
            ])
          : kind === "bokeh"
          ? buildGlowSprite(64, [
              [0, `rgba(${rgbStr},0.36)`],
              [0.74, `rgba(${rgbStr},0.32)`],
              [0.88, `rgba(${rgbStr},0.55)`],
              [1, `rgba(${rgbStr},0)`],
            ])
          : buildGlowSprite(64, [
              [0, "rgba(255,255,255,1)"],
              [0.14, `rgba(${rgbStr},0.82)`],
              [0.38, `rgba(${rgbStr},0.22)`],
              [1, `rgba(${rgbStr},0)`],
            ]);
      spritePool.set(key, spr);
      return spr;
    };

    K.prewarmSprites = (colors) => {
      for (const c of colors || []) {
        K.getGlowSprite(c, "core");
        K.getGlowSprite(c, "soft");
        K.getGlowSprite(c, "bokeh");
      }
    };
    K.prewarmSprites([palette.accent, palette.accent2, palette.ink, palette.alert]);

    K.drawSprite = (ctx, hexColor, x, y, r, alpha = 1, kind = "core") => {
      const ga = ctx.globalAlpha;
      if (alpha * ga <= 0.002 || r <= 0.2) return;
      ctx.globalAlpha = ga * alpha;
      ctx.drawImage(K.getGlowSprite(hexColor, kind), x - r, y - r, r * 2, r * 2);
      ctx.globalAlpha = ga;
    };

    K.drawHalo = (ctx, x, y, r, alpha = 0.28, hexColor = palette.accent) => {
      if (alpha <= 0.002 || r <= 1) return;
      const rgbStr = S.hexToRgb(hexColor).join(",");
      const g = ctx.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, `rgba(${rgbStr},${alpha})`);
      g.addColorStop(0.45, `rgba(${rgbStr},${alpha * 0.34})`);
      g.addColorStop(1, `rgba(${rgbStr},0)`);
      ctx.fillStyle = g;
      ctx.fillRect(x - r, y - r, r * 2, r * 2);
    };

    // ── 预烘焙 domain-warp fbm 光雾纹理 ────────────────────────
    function bakeNoiseTexture(tw, th, pixelFn) {
      const c = document.createElement("canvas");
      c.width = tw;
      c.height = th;
      const g = c.getContext("2d", { willReadFrequently: true });
      const img = g.createImageData(tw, th);
      for (let j = 0; j < th; j++) {
        for (let i = 0; i < tw; i++) {
          const [r, gr, b, a] = pixelFn(i / tw, j / th);
          const idx = (j * tw + i) * 4;
          img.data[idx] = r;
          img.data[idx + 1] = gr;
          img.data[idx + 2] = b;
          img.data[idx + 3] = a;
        }
      }
      g.putImageData(img, 0, 0);
      return c;
    }

    const acRgb = S.hexToRgb(palette.accent);
    const a2Rgb = S.hexToRgb(palette.accent2);
    const textures = {
      haze: bakeNoiseTexture(256, 144, (u, v) => {
        const q = S.fbm(u * 3, v * 3, 3, seed);
        const r = S.fbm(u * 3 + 1.8 * q + 1.3, v * 3 + 1.8 * q + 7.1, 4, seed + 5);
        const m = Math.pow(S.clamp(0.45 + 0.88 * r), 2.5) * 0.72;
        return [acRgb[0] * m * 0.58, acRgb[1] * m * 0.72, acRgb[2] * m * 0.85, 255 * S.clamp(m)];
      }),
      warmHaze: bakeNoiseTexture(256, 144, (u, v) => {
        const r = S.fbm(u * 2.6 + 3.2, v * 2.6 + S.fbm(u * 2.5, v * 2.5, 3, seed + 13), 4, seed + 17);
        const m = Math.pow(S.clamp(0.45 + r), 3.0) * 0.7;
        return [a2Rgb[0] * m, a2Rgb[1] * m, a2Rgb[2] * m, 255 * S.clamp(m)];
      }),
    };

    // ── 三层视差星空与前景微尘（固定种子预生成） ─────────────────
    const R = S.rng(seed + 202);
    const starLayers = [0, 1, 2].map((lvl) =>
      Array.from({ length: [520, 180, 42][lvl] }, () => ({
        x: R() * (W + 220) - 110,
        y: R() * (H + 180) - 90,
        s: R(),
        w: 1 + R() * 2.8,
        p: R() * S.TAU,
      }))
    );
    const dustMotes = Array.from({ length: 110 }, () => ({
      x: R() * W,
      y: R() * H,
      s: R(),
      p: R() * S.TAU,
      v: 0.35 + R() * 0.9,
    }));
    const bokehDots = Array.from({ length: 14 }, () => ({
      x: R() * W,
      y: R() * H,
      r: 18 + R() * 64,
      p: R() * S.TAU,
      a: 0.35 + R() * 0.65,
    }));

    const ambDefaults = { haze: 0.35, warm: 0.12, stars: 0.55, dust: 0.35, bokeh: 0.18, grid: 0.0, camDrift: 0.8 };
    let ambKeys = [[0, ambDefaults]];
    K.setAtmosphereKeys = (keys) => {
      ambKeys = keys.map(([t, cfg]) => [t, Object.assign({}, ambDefaults, cfg)]);
    };
    function evalAtmosphere(t) {
      let idx = 0;
      while (idx < ambKeys.length - 2 && ambKeys[idx + 1][0] <= t) idx++;
      const [t0, a] = ambKeys[idx];
      const [t1, b] = ambKeys[Math.min(idx + 1, ambKeys.length - 1)];
      const u = t1 === t0 ? 1 : S.ease.inOutSine(S.clamp((t - t0) / (t1 - t0)));
      const out = {};
      for (const k in ambDefaults) out[k] = S.lerp(a[k], b[k], u);
      return out;
    }

    // ── 对数缩放相机、震屏、闪白 ────────────────────────────────
    let cameraKeys = null;
    const shakes = [];
    const flashes = [];
    K.setCameraKeys = (keys) => {
      cameraKeys = keys;
    };
    K.addShake = (t0, amp = 9, dur = 0.24) => shakes.push([t0, amp, dur]);
    K.addFlash = (t0, peak = 0.22, dur = 0.42) => flashes.push([t0, peak, dur]);

    K.cameraAt = (t) => {
      if (!cameraKeys || !cameraKeys.length) return { z: 1, x: W / 2, y: H / 2 };
      const z = S.kfZoom(
        t,
        cameraKeys.map(([tt, zz, , , ee]) => [tt, zz, ee])
      );
      const x = S.kf(
        t,
        cameraKeys.map(([tt, , xx, , ee]) => [tt, xx, ee])
      );
      const y = S.kf(
        t,
        cameraKeys.map(([tt, , , yy, ee]) => [tt, yy, ee])
      );
      return { z, x, y };
    };

    // ── 精细视觉原语：连续大气辉光材质球、亮核、发光线描、微观放大镜 ──
    K.drawLuminousLine = (ctx, pts, hexColor = palette.accent, width = 2.6, alpha = 1) => {
      if (!pts || pts.length < 2 || alpha <= 0.002) return;
      ctx.save();
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      const passes = [
        [width * 4.4, 0.14 * alpha, hexColor],
        [width * 2.1, 0.36 * alpha, hexColor],
        [width, 0.96 * alpha, "#ffffff"],
      ];
      for (const [lw, al, col] of passes) {
        ctx.strokeStyle = S.rgba(col, al);
        ctx.lineWidth = lw;
        ctx.beginPath();
        pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
        ctx.stroke();
      }
      ctx.restore();
    };

    K.drawCore = (ctx, x, y, r, alpha = 1, hexColor = palette.accent) => {
      K.drawSprite(ctx, hexColor, x, y, r * 6.5, 0.5 * alpha, "soft");
      K.drawHalo(ctx, x, y, r * 3.0, 0.48 * alpha, hexColor);
      K.drawSprite(ctx, hexColor, x, y, r * 2.1, alpha, "core");
      K.drawSprite(ctx, "#ffffff", x, y, r * 1.05, alpha, "core");
    };

    K.drawMaterialOrb = (ctx, x, y, r, cfg = {}) => {
      const alpha = cfg.alpha ?? 1;
      if (alpha <= 0.003 || r <= 1) return;
      const baseCol = cfg.color || palette.accent;
      const rgb = S.hexToRgb(baseCol);
      const lx = x + r * (cfg.lightX ?? -0.36);
      const ly = y + r * (cfg.lightY ?? -0.4);
      ctx.save();
      ctx.globalAlpha *= alpha;
      // 外圈连续大气辉光（严禁零碎毛刺亮点）
      if ((cfg.atmo ?? 0.7) > 0) {
        const ag = ctx.createRadialGradient(x, y, r * 0.84, x, y, r * 1.48);
        ag.addColorStop(0, `rgba(${rgb.join(",")},${0.58 * (cfg.atmo ?? 0.7)})`);
        ag.addColorStop(0.45, `rgba(${rgb.join(",")},${0.16 * (cfg.atmo ?? 0.7)})`);
        ag.addColorStop(1, `rgba(${rgb.join(",")},0)`);
        ctx.fillStyle = ag;
        ctx.beginPath();
        ctx.arc(x, y, r * 1.48, 0, S.TAU);
        ctx.fill();
      }
      // 体积球体
      const body = ctx.createRadialGradient(lx, ly, r * 0.06, x, y, r);
      body.addColorStop(0, S.rgba(S.mixLinearColor(baseCol, "#ffffff", 0.58), 0.96));
      body.addColorStop(0.48, S.rgba(baseCol, 0.85));
      body.addColorStop(0.86, S.rgba(S.mixLinearColor(baseCol, "#02060f", 0.72), 0.96));
      body.addColorStop(1, S.rgba(S.mixLinearColor(baseCol, "#000000", 0.88), 0.98));
      ctx.fillStyle = body;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, S.TAU);
      ctx.fill();
      // 柔和边缘光带
      ctx.strokeStyle = S.rgba(S.mixLinearColor(baseCol, "#ffffff", 0.45), 0.75);
      ctx.lineWidth = Math.max(1.5, r * 0.018);
      ctx.beginPath();
      ctx.arc(x, y, r - 1, 0, S.TAU);
      ctx.stroke();
      // 镜面高光
      const spec = ctx.createRadialGradient(lx, ly, 0, lx, ly, r * 0.42);
      spec.addColorStop(0, "rgba(255,255,255,0.52)");
      spec.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = spec;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, S.TAU);
      ctx.fill();
      ctx.restore();
    };

    K.drawMagnifierLens = (ctx, x, y, r, drawInsideFn, cfg = {}) => {
      const col = cfg.color || palette.accent;
      ctx.save();
      ctx.beginPath();
      ctx.arc(x, y, r, 0, S.TAU);
      ctx.clip();
      ctx.fillStyle = cfg.bg || "rgba(4,9,18,0.92)";
      ctx.fillRect(x - r, y - r, r * 2, r * 2);
      if (typeof drawInsideFn === "function") drawInsideFn(ctx, x, y, r);
      ctx.restore();
      ctx.save();
      ctx.strokeStyle = S.rgba(col, 0.92);
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, S.TAU);
      ctx.stroke();
      ctx.strokeStyle = S.rgba("#ffffff", 0.28);
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(x, y, r + 9, 0, S.TAU);
      ctx.stroke();
      ctx.restore();
    };

    // ── HUD 章节角标与底部单行逐字字幕 ──────────────────────────
    let chapters = [];
    let captionLines = [];
    let captionFontMode = "sans";
    K.setChapters = (arr) => {
      chapters = arr || [];
    };
    K.setCaptions = (lines, fontMode = "sans") => {
      captionLines = lines || [];
      captionFontMode = fontMode || "sans";
    };

    const hudEl = document.createElement("div");
    hudEl.style.cssText =
      `position:absolute;left:${Math.round(W * 0.042)}px;top:${Math.round(H * 0.04)}px;` +
      `font-family:${fontSans};font-size:${Math.round(Math.min(W, H) * 0.015)}px;` +
      `letter-spacing:0.14em;color:${S.rgba(palette.ink, 0.45)};`;
    K.hudLayer.appendChild(hudEl);

    const capEl = document.createElement("div");
    capEl.style.cssText =
      "position:absolute;left:0;width:100%;text-align:center;white-space:nowrap;box-sizing:border-box;padding:0 5%;";
    K.captionLayer.appendChild(capEl);

    function parseTaggedText(raw) {
      const tokens = [];
      const re = /\[([^\]]+)\]|([^\[]+)/g;
      let m;
      while ((m = re.exec(String(raw || ""))) !== null) {
        if (m[1]) tokens.push({ text: m[1], accent: true });
        else if (m[2]) tokens.push({ text: m[2], accent: false });
      }
      return tokens;
    }

    const measureCanvas = document.createElement("canvas");
    const measureCtx = measureCanvas.getContext("2d");

    function renderCaptionAndHud(t) {
      let activeChap = null;
      for (const ch of chapters) {
        if (t >= ch[0]) activeChap = ch;
      }
      hudEl.textContent = activeChap ? `${activeChap[1]}  ${activeChap[2]}` : "";

      const cur = captionLines.find((ln) => !ln.card && t >= ln.start && t <= ln.end);
      if (!cur) {
        capEl.innerHTML = "";
        return;
      }
      const isHook = Boolean(cur.hook);
      const isPortrait = H > W;
      const basePx = isHook
        ? Math.round(isPortrait ? 76 : 98)
        : Math.round(isPortrait ? 44 : 52);
      const fontFamily = (cur.font || captionFontMode) === "serif" ? fontSerif : fontSans;
      const weight = isHook ? 900 : (cur.font || captionFontMode) === "serif" ? 600 : 500;
      const plain = String(cur.text || "").replace(/[\[\]]/g, "");
      measureCtx.font = `${weight} ${basePx}px ${fontFamily}`;
      const maxAllowW = W * (isPortrait ? 0.84 : 0.86);
      const measuredW = measureCtx.measureText(plain).width;
      const fitPx = measuredW > maxAllowW ? Math.max(26, Math.floor((basePx * maxAllowW) / measuredW)) : basePx;

      const fadeIn = S.prog(t, cur.start, cur.start + 0.22, S.ease.outCubic);
      const fadeOut = 1 - S.prog(t, cur.end - 0.22, cur.end, S.ease.inCubic);
      const alpha = Math.min(fadeIn, fadeOut);
      const posTop = isHook
        ? Math.round(H * (isPortrait ? 0.64 : 0.68))
        : Math.round(H * (isPortrait ? 0.69 : 0.875));
      capEl.style.top = `${posTop}px`;
      capEl.style.fontFamily = fontFamily;
      capEl.style.fontSize = `${fitPx}px`;
      capEl.style.fontWeight = String(weight);
      capEl.style.opacity = String(S.clamp(alpha, 0, 1));
      capEl.style.textShadow = isHook
        ? `0 6px 28px rgba(0,0,0,0.85), 0 0 28px ${S.rgba(palette.accent, 0.45)}`
        : "0 4px 16px rgba(0,0,0,0.88)";

      const tokens = parseTaggedText(cur.text);
      const totalChars = Math.max(1, plain.length);
      const revealDur = Math.min(cur.end - cur.start - 0.35, totalChars / 18);
      const shownChars = Math.floor(S.prog(t, cur.start, cur.start + Math.max(0.25, revealDur)) * totalChars) + 1;

      let cursor = 0;
      let htmlOut = "";
      for (const tk of tokens) {
        for (const ch of tk.text) {
          const vis = cursor < shownChars;
          const col = tk.accent ? palette.accent : palette.ink;
          const fw = tk.accent ? "800" : String(weight);
          htmlOut += `<span style="color:${col};font-weight:${fw};opacity:${vis ? 1 : 0};">${ch
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")}</span>`;
          cursor++;
        }
      }
      capEl.innerHTML = htmlOut;
    }

    // ── 安全区检查护栏 ─────────────────────────────────────────
    K.guardSafeBox = (label, x0, y0, x1, y1, marginX = 48, marginY = 48) => {
      if (x0 < marginX || x1 > W - marginX || y0 < marginY || y1 > H - marginY) {
        const msg = `${label} 越出安全区 [${Math.round(x0)},${Math.round(y0)},${Math.round(x1)},${Math.round(y1)}]`;
        window.__SVS_SAFE_ALERTS.push(msg);
      }
    };

    // ── 帧生命周期 begin(t) / end(t) ────────────────────────────
    K.begin = (t) => {
      for (const l of Object.values(layers)) l.clear();
      const A = evalAtmosphere(t);
      const driftX = A.camDrift * (14 * Math.sin(t * 0.065) + 6 * Math.sin(t * 0.19 + 1.1));
      const driftY = A.camDrift * (9 * Math.sin(t * 0.05 + 0.6) + 4 * Math.sin(t * 0.14));
      const breathe = 1.014 + 0.01 * A.camDrift * Math.sin((t * S.TAU) / 42);
      let shkX = 0;
      let shkY = 0;
      for (const [t0, amp, dur] of shakes) {
        const d = t - t0;
        if (d >= 0 && d < dur) {
          const k = 1 - d / dur;
          const n = Math.floor(d * 30);
          shkX += (n % 2 ? -1 : 1) * amp * k;
          shkY += (((n * 5) % 3) - 1) * amp * 0.5 * k;
        }
      }
      const cam = K.cameraAt(t);
      const z = cam.z * breathe;
      const mat = `translate(${W / 2 + driftX * 0.5 + shkX}px,${H / 2 + driftY * 0.5 + shkY}px) scale(${z}) translate(${-cam.x}px,${-cam.y}px)`;
      K.world.style.transform = mat;
      layers.main.el.style.transform = mat;
      layers.main.el.style.transformOrigin = "0 0";

      // ① 背景光雾
      const bg = K.bgCtx;
      const drawNeb = (tex, a, par, sx, sy) => {
        if (a <= 0.003) return;
        bg.save();
        bg.globalAlpha = a;
        bg.globalCompositeOperation = "lighter";
        const nw = W * 1.24;
        const nh = H * 1.24;
        bg.drawImage(
          tex,
          (W - nw) / 2 + Math.sin(t * sx) * (nw - W) * 0.4 + driftX * par,
          (H - nh) / 2 + Math.cos(t * sy) * (nh - H) * 0.4 + driftY * par,
          nw,
          nh
        );
        bg.restore();
      };
      drawNeb(textures.haze, A.haze, 0.2, 0.013, 0.009);
      drawNeb(textures.warmHaze, A.warm, 0.25, 0.01, 0.014);

      // ② 环境网格与三层视差星空
      const g = K.bg2Ctx;
      if (A.grid > 0.01) {
        const ox = (driftX * 0.35) % 48;
        const oy = (driftY * 0.35) % 48;
        g.strokeStyle = S.rgba(palette.ink, 0.04 * A.grid);
        g.lineWidth = 1;
        g.beginPath();
        for (let x = -48 + ox; x < W + 48; x += 48) {
          g.moveTo(x, 0);
          g.lineTo(x, H);
        }
        for (let y = -48 + oy; y < H + 48; y += 48) {
          g.moveTo(0, y);
          g.lineTo(W, y);
        }
        g.stroke();
      }
      if (A.stars > 0.01) {
        starLayers.forEach((arr, lvl) => {
          const par = [0.15, 0.42, 0.85][lvl];
          const base = [0.42, 0.68, 0.95][lvl] * A.stars;
          for (const st of arr) {
            const x = st.x + driftX * par * 1.8;
            const y = st.y + driftY * par * 1.8;
            const al = base * (0.25 + 0.75 * st.s) * (0.55 + 0.45 * Math.sin(t * st.w + st.p));
            if (lvl === 2) {
              K.drawSprite(g, st.s > 0.68 ? palette.accent : "#ffffff", x, y, 3.5 + st.s * 7.5, al * 0.85, "core");
            } else {
              g.fillStyle = lvl === 0 ? S.rgba(palette.accent, al) : S.rgba(palette.ink, al);
              g.fillRect(x, y, 1 + lvl * 0.6, 1 + lvl * 0.6);
            }
          }
        });
      }

      // ⑥ 前景微尘与虚焦光斑
      const fg = K.fgCtx;
      if (A.dust > 0.01) {
        for (const d of dustMotes) {
          const x = (((d.x + Math.sin(t * 0.2 * d.v + d.p) * 36 + t * 5 * d.v + driftX * 1.5) % (W + 40)) + (W + 40)) % (W + 40) - 20;
          const y = (((d.y + Math.cos(t * 0.16 * d.v + d.p) * 28 - t * 3 * d.v + driftY * 1.5) % (H + 40)) + (H + 40)) % (H + 40) - 20;
          fg.fillStyle = S.rgba(d.s > 0.8 ? palette.accent : palette.ink, A.dust * (0.12 + 0.38 * d.s));
          fg.beginPath();
          fg.arc(x, y, 0.7 + d.s * 1.3, 0, S.TAU);
          fg.fill();
        }
      }
      if (A.bokeh > 0.01) {
        for (const b of bokehDots) {
          const x = (((b.x + t * 8 + Math.sin(t * 0.1 + b.p) * 54 + driftX * 2.3) % (W + 180)) + (W + 180)) % (W + 180) - 90;
          K.drawSprite(fg, palette.accent, x, b.y + Math.cos(t * 0.08 + b.p) * 34 + driftY * 2.3, b.r, A.bokeh * 0.08 * b.a, "bokeh");
        }
      }
    };

    K.end = (t) => {
      // 1/4 分辨率阈值 Bloom 叠加
      if (bloomStrength > 0) {
        bThreshCtx.clearRect(0, 0, bW, bH);
        bThreshCtx.filter = "brightness(0.55) contrast(3.1)";
        bThreshCtx.drawImage(layers.main.el, 0, 0, bW, bH);
        bThreshCtx.filter = "none";
        bBlurCtx.clearRect(0, 0, bW, bH);
        bBlurCtx.filter = "blur(5px)";
        bBlurCtx.drawImage(bThresh, 0, 0);
        bBlurCtx.filter = "none";
        const bc = layers.bloom.ctx;
        bc.save();
        bc.globalAlpha = S.clamp(bloomStrength, 0, 1);
        bc.drawImage(bBlur, 0, 0, W, H);
        bc.restore();
        layers.bloom.el.style.transformOrigin = "0 0";
        layers.bloom.el.style.transform = layers.main.el.style.transform;
      }

      // 受控闪白
      let fl = 0;
      for (const [t0, peak, dur] of flashes) {
        const d = t - t0;
        if (d >= 0 && d < dur) fl = Math.max(fl, peak * Math.pow(1 - d / dur, 2));
      }
      flashLayer.style.opacity = String(fl);

      // HUD 与单行字幕（读 frameCenterT 防子帧模糊重影）
      renderCaptionAndHud(S.frameT ?? t);

      // 24fps 确定性胶片颗粒
      const gr = grainCanvas.ctx;
      const gRng = S.rng(Math.floor((S.frameT ?? t) * 24) + seed * 7 + 1);
      grainCanvas.clear();
      for (let i = 0; i < 1600; i++) {
        gr.fillStyle = gRng() > 0.5 ? "rgba(255,255,255,0.14)" : "rgba(0,0,0,0.14)";
        gr.fillRect(gRng() * W, gRng() * H, 2, 2);
      }
    };

    return K;
  }

  window.SVSVisualKit = { create: createVisualKit };
})();
