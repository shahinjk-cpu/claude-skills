(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  let state = {
    status: null,
    skills: [],
    logs: [],
    activity: { items: [], stats: { total: 0, ok: 0, errors: 0, avgMs: 0 } },
    expandedActs: new Set(),
    diagnostics: null,
    skillFilter: "All",
    provFilter: "All",
    actFilter: "all",
    tkLoaded: false,
    auditMode: "code",
    lastAudit: null,
    modules: [],
    modFilter: "All",
    activeModule: null,
    styles: {},
    genres: [],
    selectedGenre: "classic",
    antiSlop: "",
    recovery: [],
    memory: [],
    lastRoute: null,
    editingId: null,
    motion: true,
    accent: "indigo",
    liquidGlass: true,
    backdrop: "sunset",
    glass: "liquid",
  };
  const _sig = { pinned: "", providers: "", presets: "", starter: "", custom: "", servers: "", tools: "", activity: "" };

  // ── Smooth rAF Ambient Motion & Liquid Glass Pointer Sheen ────────────
  function startAmbientCanvas() {
    const canvas = $("#bg-matrix");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let t = 0;
    let lastTs = 0;
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);
    const draw = (ts) => {
      requestAnimationFrame(draw);
      if (document.hidden || !state.motion || reduced) {
        if (!state.motion) ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
      }
      if (ts - lastTs < 42) return;
      lastTs = ts;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      t += 0.024;
      const gap = 38;
      for (let x = 18; x < canvas.width; x += gap) {
        for (let y = 18; y < canvas.height; y += gap) {
          const wave = Math.sin((x + y) * 0.0075 + t) * 0.5 + 0.5;
          ctx.fillStyle = `rgba(255, 255, 255, ${(0.025 + wave * 0.055).toFixed(3)})`;
          ctx.fillRect(x, y, 1.5, 1.5);
        }
      }
    };
    requestAnimationFrame(draw);
  }

  function startPointerSheen() {
    let raf = 0;
    let lastEvent = null;
    document.addEventListener("pointermove", (e) => {
      lastEvent = e;
      if (raf || !state.motion) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const ev = lastEvent;
        if (!ev) return;
        const card = ev.target && ev.target.closest ? ev.target.closest(".hero-card, .provider-card, .guide-card, .skill-card, .server-card, .settings-card, .surface-card, .prompt-card, .quick-card") : null;
        if (!card) return;
        const r = card.getBoundingClientRect();
        card.style.setProperty("--mx", `${Math.round(ev.clientX - r.left)}px`);
        card.style.setProperty("--my", `${Math.round(ev.clientY - r.top)}px`);
      });
    }, { passive: true });
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  async function api(path, body = null) {
    const opts = body !== null
      ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
      : { method: "GET" };
    const r = await fetch(path, opts);
    return await r.json();
  }

  function toast(msg) {
    const el = $("#toast");
    if (!el) return;
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.hidden = true; }, 3200);
  }

  function esc(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function copyText(text, okMsg = "Copied to clipboard.") {
    try {
      await navigator.clipboard.writeText(text);
      toast(okMsg);
    } catch {
      toast("Copy failed.");
    }
  }

  function greetingPrefix() {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 18) return "Good afternoon";
    return "Good evening";
  }

  function formatUptime(sec) {
    const s = Math.max(0, Number(sec || 0));
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  }

  function applyTheme(settings) {
    const accent = (settings && settings.accentTheme) || "indigo";
    const liquidGlass = !settings || settings.liquidGlass !== false;
    const backdrop = (settings && settings.liquidBackdrop) || "sunset";
    const glass = (settings && settings.glassStyle) || "liquid";
    state.accent = accent;
    state.liquidGlass = liquidGlass;
    state.backdrop = backdrop;
    state.glass = glass;
    state.motion = !settings || settings.ambientMotion !== false;
    document.documentElement.setAttribute("data-accent", accent);
    document.documentElement.setAttribute("data-liquid", liquidGlass ? "on" : "off");
    document.documentElement.setAttribute("data-backdrop", backdrop);
    document.documentElement.setAttribute("data-glass", glass);
    document.documentElement.setAttribute("data-motion", state.motion ? "on" : "off");
    $$("[data-accent-pick]").forEach((b) =>
      b.classList.toggle("active", b.dataset.accentPick === accent)
    );
    $$("[data-backdrop-pick]").forEach((b) =>
      b.classList.toggle("active", b.dataset.backdropPick === backdrop)
    );
    $$("[data-glass-pick]").forEach((b) =>
      b.classList.toggle("active", b.dataset.glassPick === glass)
    );
  }

  function animateCount(el, nextVal) {
    if (!el) return;
    const target = Number(nextVal) || 0;
    const prev = Number(el.dataset.numVal);
    if (Number.isNaN(prev) || prev === target || !state.motion) {
      el.dataset.numVal = String(target);
      el.textContent = String(target);
      return;
    }
    el.dataset.numVal = String(target);
    const start = performance.now();
    const dur = 320;
    const step = (now) => {
      const p = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = String(Math.round(prev + (target - prev) * eased));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  // ── Navigation ────────────────────────────────────────────────────────
  const VIEW_META = {
    home: { eyebrow: "— HOME", sub: "Bridge online. Pick an AI, equip playbooks, build." },
    activity: { eyebrow: "— ACTIVITY", sub: "Real-time inspector for every MCP tool call executed by your AIs." },
    environment: { eyebrow: "— SKILLS", sub: "17 AAA Roblox Studio playbooks for 1:1 cloning, animations, security, UI, combat & more." },
    toolkit: { eyebrow: "— TOOLKIT", sub: "60-gate static Luau Auditor, 19 starter Luau modules, 12-genre style tokens & project memory." },
    prompts: { eyebrow: "— PROMPTS", sub: "Global instructions synced across all 12 AIs plus reusable developer templates." },
    connections: { eyebrow: "— CONNECTIONS", sub: "Health Doctor diagnostics, MCP processes, and live Studio command browser." },
    settings: { eyebrow: "— SETTINGS", sub: "Personalize Liquid Glass mode, scenic backdrop, accent theme, and tray behavior." },
  };

  function switchView(view) {
    $$("#side-nav .nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
    const meta = VIEW_META[view] || VIEW_META.home;
    $("#page-eyebrow").textContent = meta.eyebrow;
    if (view === "home") {
      const name = (state.status && state.status.settings && state.status.settings.userName) || "Builder";
      $("#page-title").textContent = `${greetingPrefix()}, ${name}`;
    } else {
      const titles = { environment: "Skills & Playbooks", toolkit: "ZeroScript Toolkit", connections: "Connections & Doctor", prompts: "Prompt Studio", activity: "Live Activity", settings: "Settings" };
      $("#page-title").textContent = titles[view] || (view.charAt(0).toUpperCase() + view.slice(1));
    }
    $("#page-sub").textContent = meta.sub;
    if (view === "environment") loadSkills();
    if (view === "toolkit") loadToolkitSummary();
    if (view === "activity") loadActivity();
    if (view === "connections" && !state.diagnostics) runDiagnostics();
  }

  function switchSubtab(name) {
    $$(".subtab").forEach((b) => b.classList.toggle("active", b.dataset.subtab === name));
    $$(".subpanel").forEach((p) => p.classList.toggle("active", p.id === `sub-${name}`));
  }

  function switchTkTab(name) {
    $$(".tk-tab").forEach((b) => b.classList.toggle("active", b.dataset.tktab === name));
    $$(".tk-panel").forEach((p) => p.classList.toggle("active", p.id === `tk-${name}`));
  }

  // ── Render Status & Views ─────────────────────────────────────────────
  function renderStatus(s) {
    state.status = s;
    if (!s || !s.ok) return;

    const br = s.bridge || {};
    const st = s.studio || {};
    const servers = s.servers || [];
    const tools = s.tools || [];
    const settings = s.settings || {};
    const providers = s.providers || [];
    const stats = s.activityStats || {};

    applyTheme(settings);

    $("#brand-ver").textContent = `V${br.version || "1.9.1"}`;
    const name = settings.userName || "Builder";
    $("#profile-name").textContent = name;
    $("#profile-avatar").textContent = name.charAt(0).toUpperCase();
    $("#profile-role").textContent = `${providers.length} AI · LOCAL BRIDGE`;
    if ($("#view-home").classList.contains("active")) {
      $("#page-title").textContent = `${greetingPrefix()}, ${name}`;
    }

    // Settings & Global Prompt bindings (avoid overwriting while actively focused)
    if (document.activeElement !== $("#set-username")) $("#set-username").value = name;
    if (document.activeElement !== $("#global-prompt-input")) {
      $("#global-prompt-input").value = settings.globalPrompt || "";
    }
    $("#set-liquid-glass").checked = settings.liquidGlass !== false;
    $("#set-motion").checked = settings.ambientMotion !== false;
    $("#set-tray").checked = settings.minimizeToTray !== false;
    $("#set-autoopen").checked = settings.autoOpenWindow !== false;

    if (s.paths) {
      $("#path-ext").textContent = s.paths.extension;
      $("#path-skills").textContent = s.paths.skills;
      if ($("#path-modules") && s.paths.modules) $("#path-modules").textContent = s.paths.modules;
      $("#path-logs").textContent = s.paths.logs;
    }

    // Header pill + pipeline diagram
    const pill = $("#header-pill");
    const pillTxt = $("#header-pill-txt");
    const diagBox = $("#diagram-status");
    const diagTxt = $("#diagram-status-txt");
    pill.classList.remove("warn", "off");
    diagBox.classList.remove("warn", "off");

    if (!br.online) {
      pill.classList.add("off");
      pillTxt.textContent = "BRIDGE OFFLINE";
      diagBox.classList.add("off");
      diagTxt.textContent = "Bridge offline · attempting startup";
    } else if (st.place === true) {
      pillTxt.textContent = "STUDIO READY";
      diagTxt.textContent = `Studio attached · ${tools.length} commands ready`;
    } else if (st.app === true) {
      pill.classList.add("warn");
      pillTxt.textContent = "NO PLACE OPEN";
      diagBox.classList.add("warn");
      diagTxt.textContent = "Studio open · open a place to attach";
    } else {
      pill.classList.add("warn");
      pillTxt.textContent = "BRIDGE ONLINE";
      diagTxt.textContent = `Bridge online · ${br.clients || 0} tab(s) connected`;
    }

    $("#diag-tabs").textContent = `${br.clients || 0} active tab(s)`;
    $("#diag-tools-sub").textContent = `${tools.length} commands`;
    $("#hero-uptime").textContent = `UPTIME ${formatUptime(br.uptime)}`;
    const enabledSkills = (s.skills || []).filter((sk) => sk.enabled).length;
    $("#hero-skills-pill").textContent = `${enabledSkills} SKILLS READY`;
    $("#prov-count-pill").textContent = String(providers.length);
    $("#nav-activity-badge").textContent = String(stats.total || 0);

    // Overview KPIs
    animateCount($("#kpi-commands"), tools.length);
    if (st.place === true) {
      $("#kpi-studio").textContent = "Connected";
      $("#kpi-studio-sub").textContent = "Place active and ready.";
    } else if (st.app === true) {
      $("#kpi-studio").textContent = "No place";
      $("#kpi-studio-sub").textContent = "Open a place in Roblox Studio.";
    } else if (st.proc === true) {
      $("#kpi-studio").textContent = "MCP waiting";
      $("#kpi-studio-sub").textContent = "Open Assistant Settings > MCP Servers.";
    } else {
      $("#kpi-studio").textContent = "Waiting";
      $("#kpi-studio-sub").textContent = "Open Roblox Studio & a place.";
    }

    animateCount($("#kpi-activity"), stats.total || 0);
    $("#kpi-activity-sub").textContent = stats.total ? `${stats.avgMs || 0}ms avg · ${stats.errors || 0} errors` : "No tool calls yet";

    animateCount($("#kpi-skills-kpi"), enabledSkills);
    $("#kpi-skills-sub").textContent = `${(s.skills || []).length} total playbooks installed`;
    $("#quick-skills-sub").textContent = `${enabledSkills} active playbooks & ${(s.presets || []).length} preset packs`;
    if (s.toolkit) {
      const tk = s.toolkit;
      if ($("#nav-toolkit-badge")) $("#nav-toolkit-badge").textContent = String(tk.gates || 60);
      if ($("#tk-mod-count")) $("#tk-mod-count").textContent = String(tk.modules || 19);
      if ($("#tk-mem-count")) $("#tk-mem-count").textContent = String(tk.memoryCount || 0);
      if ($("#quick-toolkit-sub")) {
        $("#quick-toolkit-sub").textContent = `${tk.gates || 60}-gate scanner, ${tk.modules || 19} modules & ${tk.memoryCount || 0} memory`;
      }
    }

    renderPinnedProviders(providers, settings.favoriteProviders || []);
    renderProviders(providers, settings.favoriteProviders || []);
    renderPresets(s.presets || []);
    renderPrompts(s.starterPrompts || [], settings.customPrompts || []);
    renderConnections(servers, tools);
  }

  function renderPinnedProviders(providers, favIds) {
    const row = $("#pinned-providers-row");
    if (!row) return;
    const favSet = new Set(favIds);
    let picks = providers.filter((p) => favSet.has(p.id));
    if (!picks.length) picks = providers.slice(0, 3);
    const sig = picks.map((p) => p.id).join(",");
    if (sig === _sig.pinned) return;
    _sig.pinned = sig;
    row.innerHTML = picks.map((p) => `
      <button class="pinned-chip" data-url="${esc(p.url)}">
        <span class="pinned-dot" style="background:${esc(p.color || "#818cf8")}"></span>
        ${esc(p.name)}
      </button>
    `).join("");
  }

  function renderProviders(providers, favIds) {
    const grid = $("#providers-grid");
    if (!grid) return;
    const favSet = new Set(favIds || []);
    const q = ($("#prov-search")?.value || "").trim().toLowerCase();
    const filtered = providers.filter((p) => {
      if (state.provFilter !== "All" && (p.category || "").toLowerCase() !== state.provFilter.toLowerCase()) return false;
      if (q && !`${p.name} ${p.desc} ${p.tag} ${p.category}`.toLowerCase().includes(q)) return false;
      return true;
    });
    const sig = `${state.provFilter}|${q}|${filtered.map((p) => `${p.id}:${favSet.has(p.id) ? 1 : 0}`).join(",")}`;
    if (sig === _sig.providers) return;
    _sig.providers = sig;

    grid.innerHTML = filtered.map((p) => {
      const isFav = favSet.has(p.id);
      return `
        <div class="provider-card">
          <div>
            <div class="prov-head">
              <div class="prov-ident">
                <div class="prov-badge" style="background:${esc(p.color || "#818cf8")}">${esc(p.badge || p.name.slice(0, 2).toUpperCase())}</div>
                <div class="prov-name">${esc(p.name)}</div>
              </div>
              <button class="fav-btn ${isFav ? "active" : ""}" data-fav-prov="${esc(p.id)}" title="${isFav ? "Unpin from Home" : "Pin to Home"}">${isFav ? "★" : "☆"}</button>
            </div>
            <div class="prov-tags">
              <span class="tag ${p.vision ? "green" : ""}">${esc(p.vision ? "Vision" : "Text")}</span>
              <span class="tag accent">${esc(p.tag)}</span>
            </div>
            <p class="prov-desc">${esc(p.desc)}</p>
          </div>
          <div class="prov-foot">
            <button class="btn-primary sm" data-url="${esc(p.url)}">LAUNCH ${esc(p.name)} →</button>
          </div>
        </div>
      `;
    }).join("") || `<div class="sec-sub">No matching AI providers.</div>`;
  }

  // ── Activity View ─────────────────────────────────────────────────────
  async function loadActivity() {
    try {
      const res = await api("/api/activity");
      if (res && res.ok) {
        state.activity = { items: res.items || [], stats: res.stats || {} };
        renderActivity();
      }
    } catch {}
  }

  function renderActivity() {
    const st = state.activity.stats || {};
    const total = st.total || 0;
    const ok = st.ok || 0;
    const err = st.errors || 0;
    const rate = total ? Math.round((ok / total) * 100) : 100;

    $("#act-total").textContent = String(total);
    $("#act-ok").textContent = String(ok);
    $("#act-rate").textContent = `${rate}% success rate`;
    $("#act-err").textContent = String(err);
    $("#act-ms").textContent = `${st.avgMs || 0}ms`;
    $("#nav-activity-badge").textContent = String(total);

    const list = $("#activity-list");
    if (!list) return;
    const q = ($("#activity-search")?.value || "").trim().toLowerCase();
    const filtered = (state.activity.items || []).filter((it) => {
      if (state.actFilter === "ok" && !it.ok) return false;
      if (state.actFilter === "err" && it.ok) return false;
      if (q && !`${it.tool} ${it.server} ${it.args} ${it.preview}`.toLowerCase().includes(q)) return false;
      return true;
    });
    const sig = `${state.actFilter}|${q}|${filtered.map((it) => `${it.id}:${it.ok ? 1 : 0}:${state.expandedActs.has(it.id) ? 1 : 0}`).join(",")}`;
    if (sig === _sig.activity) return;
    _sig.activity = sig;

    list.innerHTML = filtered.map((it) => `
      <div class="act-card">
        <div class="act-head" data-toggle-act="${it.id}">
          <div class="act-left">
            <span class="act-dot ${it.ok ? "" : "err"}"></span>
            <span class="act-tool">${esc(it.tool)}</span>
            <span class="tag">${esc(it.server)}</span>
            ${it.images ? `<span class="tag accent">${it.images} img</span>` : ""}
          </div>
          <div class="act-right">
            <button class="btn-outline sm" data-copy-act="${it.id}" title="Copy command JSON">COPY</button>
            <span class="tag ${it.ok ? "green" : "red"}">${it.ok ? "OK" : "ERROR"}</span>
            <span class="tag">${it.ms}ms</span>
            <span class="act-ts">${esc(it.ts)}</span>
          </div>
        </div>
        <div class="act-detail" id="act-det-${it.id}" ${state.expandedActs.has(it.id) ? "" : "hidden"}>
          <div>
            <div class="act-box-label">Arguments</div>
            <pre class="act-pre">${esc(it.args || "{}")}</pre>
          </div>
          <div>
            <div class="act-box-label">Output Preview</div>
            <pre class="act-pre">${esc(it.preview || "(empty)")}</pre>
          </div>
        </div>
      </div>
    `).join("") || `<div class="surface-card"><div class="sec-sub">No tool calls recorded yet. Start an AI agent in any supported browser tab to inspect live Studio execution here.</div></div>`;
  }

  // ── Skills & Presets View ─────────────────────────────────────────────
  function renderPresets(presets) {
    const row = $("#presets-row");
    if (!row) return;
    const sig = (presets || []).map((p) => p.id).join(",");
    if (sig === _sig.presets) return;
    _sig.presets = sig;
    row.innerHTML = presets.map((p) => `
      <button class="preset-btn" data-preset="${esc(p.id)}">
        <div class="preset-name">${esc(p.name)}</div>
        <div class="preset-desc">${esc(p.desc)}</div>
      </button>
    `).join("");
  }

  async function loadSkills() {
    const res = await api("/api/skills");
    if (res && res.ok) {
      state.skills = res.skills || [];
      renderSkills();
    }
  }

  function renderSkills() {
    const grid = $("#skills-grid");
    if (!grid) return;
    const cat = state.skillFilter;
    const q = ($("#skill-search")?.value || "").trim().toLowerCase();
    const list = state.skills.filter((s) => {
      if (cat !== "All" && (s.category || "").toLowerCase() !== cat.toLowerCase()) return false;
      if (q && !`${s.name} ${s.tagline} ${s.category} ${s.id}`.toLowerCase().includes(q)) return false;
      return true;
    });

    grid.innerHTML = list.map((s) => `
      <div class="skill-card ${s.enabled ? "" : "disabled"}">
        <div class="skill-top">
          <span class="tag accent">${esc(s.category || "Custom")}</span>
          <span class="tag">${s.builtin ? "Built-in" : "Custom"} · ${Math.round((s.chars || 0) / 100) / 10}k chars</span>
        </div>
        <h3 class="skill-title">${esc(s.name)}</h3>
        <p class="skill-tagline">${esc(s.tagline || "Specialized agent playbook.")}</p>
        <div class="skill-controls">
          <div class="mode-switch" title="Auto lets the agent read on demand; Always embeds in every session start">
            <button class="mode-btn ${s.mode === "auto" ? "active" : ""}" data-skill-mode="auto" data-id="${esc(s.id)}">AUTO</button>
            <button class="mode-btn ${s.mode === "always" ? "active" : ""}" data-skill-mode="always" data-id="${esc(s.id)}">ALWAYS</button>
          </div>
          <div class="toolbar-actions">
            <button class="btn-outline sm" data-edit-skill="${esc(s.id)}">EDIT</button>
            <button class="btn-outline sm" data-export-skill="${esc(s.id)}" title="Download Markdown file">EXPORT</button>
            ${!s.builtin ? `<button class="btn-outline sm" data-del-skill="${esc(s.id)}">DEL</button>` : ""}
            <label class="switch" title="Enable / disable skill">
              <input type="checkbox" data-toggle-skill="${esc(s.id)}" ${s.enabled ? "checked" : ""} />
              <span class="switch-track"></span>
            </label>
          </div>
        </div>
      </div>
    `).join("") || `<div class="sec-sub">No matching skills found.</div>`;
  }

  function openSkillModal(skill = null) {
    state.editingId = skill ? skill.id : null;
    $("#skill-modal-eyebrow").textContent = skill ? "— EDIT SKILL PLAYBOOK" : "— CREATE CUSTOM SKILL";
    $("#skill-modal-title").textContent = skill ? skill.name : "New Agent Skill";
    $("#sk-name").value = skill ? skill.name : "";
    $("#sk-id").value = skill ? skill.id : "";
    $("#sk-id").disabled = !!(skill && skill.builtin);
    $("#sk-cat").value = skill ? (skill.category || "Custom") : "Custom";
    $("#sk-mode").value = skill ? (skill.mode || "auto") : "auto";
    $("#sk-tagline").value = skill ? (skill.tagline || "") : "";
    $("#sk-content").value = skill ? (skill.content || "") : "# Custom Skill Playbook\n\nDescribe the rules, standards, and workflows the AI agent should follow:\n";
    $("#skill-form-msg").textContent = "";
    $("#skill-modal").hidden = false;
  }

  function exportSkillMarkdown(sk) {
    const q = (v) => `"${String(v || "").replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
    const md = `---\nid: ${sk.id}\nname: ${q(sk.name)}\ncategory: ${q(sk.category)}\ntagline: ${q(sk.tagline || "")}\nenabled: ${sk.enabled ? "true" : "false"}\nmode: ${sk.mode || "auto"}\n---\n\n${sk.content || ""}\n`;
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${sk.id}.md`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    toast(`Exported ${sk.id}.md`);
  }

  // ── Prompts View ──────────────────────────────────────────────────────
  function renderPrompts(starter, custom) {
    const sGrid = $("#starter-prompts-grid");
    const sSig = JSON.stringify(starter || []);
    if (sGrid && sSig !== _sig.starter) {
      _sig.starter = sSig;
      sGrid.innerHTML = starter.map((p, idx) => `
        <div class="prompt-card">
          <div class="skill-top">
            <span class="tag accent">${esc(p.category || "Starter")}</span>
            <button class="btn-outline sm" data-copy-prompt="${idx}" data-source="starter">COPY</button>
          </div>
          <div class="prompt-title">${esc(p.title)}</div>
          <div class="prompt-body">${esc(p.text)}</div>
        </div>
      `).join("");
    }

    const cGrid = $("#custom-prompts-grid");
    const cSig = JSON.stringify(custom || []);
    if (cGrid && cSig !== _sig.custom) {
      _sig.custom = cSig;
      cGrid.innerHTML = (custom || []).map((p) => `
        <div class="prompt-card">
          <div class="skill-top">
            <span class="tag green">${esc(p.category || "Custom")}</span>
            <div class="toolbar-actions">
              <button class="btn-outline sm" data-copy-custom="${esc(p.id)}">COPY</button>
              <button class="btn-outline sm" data-del-custom="${esc(p.id)}">DEL</button>
            </div>
          </div>
          <div class="prompt-title">${esc(p.title)}</div>
          <div class="prompt-body">${esc(p.text)}</div>
        </div>
      `).join("") || `<div class="surface-card"><div class="sec-sub">No saved personal prompts yet. Click "+ Save Prompt" to build your reusable snippet library.</div></div>`;
    }
  }

  // ── Connections & Health Doctor ───────────────────────────────────────
  async function runDiagnostics() {
    const box = $("#diag-list");
    if (box) box.innerHTML = `<div class="sec-sub">Running diagnostics...</div>`;
    try {
      const res = await api("/api/diagnostics");
      if (res && res.ok) {
        state.diagnostics = res;
        renderDiagnostics(res);
      }
    } catch {
      if (box) box.innerHTML = `<div class="sec-sub">Diagnostics check failed.</div>`;
    }
  }

  function renderDiagnostics(res) {
    const box = $("#diag-list");
    if (!box || !res) return;
    const iconFor = { ok: "✓", warn: "!", fail: "✕" };
    box.innerHTML = (res.checks || []).map((c) => `
      <div class="diag-row">
        <div class="diag-ic ${esc(c.status)}">${iconFor[c.status] || "!"}</div>
        <div>
          <div class="diag-name">${esc(c.title)}</div>
          <div class="diag-detail">${esc(c.detail)}</div>
        </div>
      </div>
    `).join("");
  }

  function renderConnections(servers, tools) {
    const sList = $("#servers-list");
    const srvSig = JSON.stringify(servers || []);
    if (sList && srvSig !== _sig.servers) {
      _sig.servers = srvSig;
      sList.innerHTML = servers.map((sv) => `
        <div class="server-card">
          <div class="srv-top">
            <strong>${esc(sv.id)}</strong>
            <span class="tag ${sv.alive ? "green" : "amber"}">${sv.alive ? `Online · ${sv.tools} tools` : "Offline"}</span>
          </div>
          <div class="srv-cmd">${esc(sv.command)} ${esc((sv.args || []).join(" "))}</div>
          ${sv.startError ? `<div class="srv-err">${esc(sv.startError)}</div>` : ""}
          <div class="srv-actions">
            <button class="btn-outline sm" data-restart-srv="${esc(sv.id)}">RESTART</button>
            ${sv.id !== "roblox" ? `<button class="btn-outline sm" data-remove-srv="${esc(sv.id)}">REMOVE</button>` : ""}
          </div>
        </div>
      `).join("");
    }

    const q = ($("#tool-search")?.value || "").trim().toLowerCase();
    const filtered = q
      ? tools.filter((t) => `${t.name} ${t.description} ${t.server}`.toLowerCase().includes(q))
      : tools;
    $("#tools-count-sub").textContent = `${filtered.length} of ${tools.length} commands · click any command to copy JSON`;
    const tList = $("#tools-list");
    const toolSig = `${q}|${filtered.map((t) => `${t.server}/${t.name}`).join(",")}`;
    if (tList && toolSig !== _sig.tools) {
      _sig.tools = toolSig;
      tList.innerHTML = filtered.map((t) => `
        <div class="tool-row" data-copy-tool="${esc(t.name)}">
          <div class="tool-head">
            <span class="tool-name">${esc(t.name)}</span>
            <span class="tag">${esc(t.server)}</span>
          </div>
          ${t.description ? `<div class="tool-desc">${esc(t.description)}</div>` : ""}
        </div>
      `).join("") || `<div class="sec-sub">No matching commands loaded.</div>`;
    }
  }

  // ── Command Palette (Ctrl+K) ──────────────────────────────────────────
  let _paletteIndex = 0;
  function openPalette() {
    $("#cmd-palette").hidden = false;
    const inp = $("#palette-input");
    inp.value = "";
    _paletteIndex = 0;
    renderPalette("");
    requestAnimationFrame(() => inp.focus());
  }

  function buildPaletteEntries() {
    const out = [
      { title: "Go to Home Overview", sub: "Navigation", badge: "VIEW", run: () => { switchView("home"); switchSubtab("overview"); } },
      { title: "Go to Live Activity Inspector", sub: "Inspect MCP tool calls", badge: "VIEW", run: () => switchView("activity") },
      { title: "Go to Skills & Presets", sub: "Manage 17 AAA AI playbooks", badge: "VIEW", run: () => switchView("environment") },
      { title: "Go to Toolkit (Luau Auditor, Modules & Memory)", sub: "60-gate analyzer, 19 Luau modules & style tokens", badge: "VIEW", run: () => switchView("toolkit") },
      { title: "Toolkit: 60-Gate Luau Auditor", sub: "Scan any Luau script or Rojo folder", badge: "TOOLKIT", run: () => { switchView("toolkit"); switchTkTab("auditor"); } },
      { title: "Toolkit: 19 Battle-Tested Luau Modules", sub: "TokenBucket, AttackWindow, CriticalSpring, StudioProbe...", badge: "TOOLKIT", run: () => { switchView("toolkit"); switchTkTab("modules"); } },
      { title: "Toolkit: 12-Genre Style Vocab & Bug Guide", sub: "Style grammar, anti-slop & recovery recipes", badge: "TOOLKIT", run: () => { switchView("toolkit"); switchTkTab("guides"); } },
      { title: "Toolkit: Local Project Memory Ledger", sub: "Shared architecture facts for all AIs", badge: "TOOLKIT", run: () => { switchView("toolkit"); switchTkTab("memory"); } },
      { title: "Go to Prompt Studio", sub: "Global instructions & starter prompts", badge: "VIEW", run: () => switchView("prompts") },
      { title: "Go to Connections & Health Doctor", sub: "MCP servers, commands & diagnostics", badge: "VIEW", run: () => { switchView("connections"); runDiagnostics(); } },
      { title: "Go to Settings & Liquid Glass", sub: "Liquid Glass mode, backdrops & themes", badge: "VIEW", run: () => switchView("settings") },
      { title: `${state.liquidGlass ? "Disable" : "Enable"} Liquid Glass Mode`, sub: "Toggle translucent blown-glass UI", badge: "GLASS", run: () => api("/api/settings", { liquidGlass: !state.liquidGlass }).then((r) => { if (r.ok && state.status) { state.status.settings = r.settings; applyTheme(r.settings); $("#set-liquid-glass").checked = r.settings.liquidGlass; toast(`Liquid Glass ${r.settings.liquidGlass ? "enabled" : "disabled"}.`); } }) },
      { title: "Refresh Bridge & Studio Status", sub: "Action", badge: "ACTION", run: () => refreshNow() },
      { title: "Restart Roblox MCP Proxy", sub: "Action", badge: "ACTION", run: () => api("/api/restart_mcp", { server: "roblox" }).then((r) => { if (r.ok) renderStatus(r); toast("Roblox MCP restarted."); }) },
      { title: "Open Chrome Extension Folder", sub: "Load unpacked extension", badge: "FOLDER", run: () => api("/api/open_folder", { folder: "extension" }) },
      { title: "Open Bridge Logs Drawer", sub: "Telemetry", badge: "LOGS", run: () => { $("#logs-drawer").hidden = false; loadLogs(); } },
    ];
    for (const bd of ["sunset", "aurora", "ocean", "midnight"]) {
      out.push({
        title: `Liquid Backdrop: ${bd.charAt(0).toUpperCase() + bd.slice(1)}`,
        sub: "Switch scenic atmospheric refraction backdrop",
        badge: "BACKDROP",
        run: () => api("/api/settings", { liquidGlass: true, liquidBackdrop: bd }).then((r) => { if (r.ok && state.status) { state.status.settings = r.settings; applyTheme(r.settings); toast(`Backdrop: ${bd}`); } }),
      });
    }
    for (const gs of ["liquid", "frosted", "crystal"]) {
      out.push({
        title: `Glass Style: ${gs.charAt(0).toUpperCase() + gs.slice(1)}`,
        sub: "Switch workspace glass surface style",
        badge: "GLASS",
        run: () => api("/api/settings", { glassStyle: gs }).then((r) => { if (r.ok && state.status) { state.status.settings = r.settings; applyTheme(r.settings); toast(`Glass style: ${gs}`); } }),
      });
    }
    for (const p of ((state.status && state.status.providers) || [])) {
      out.push({ title: `Launch ${p.name}`, sub: `${p.tag} · ${p.url}`, badge: "AI", run: () => api("/api/open_url", { url: p.url }) });
    }
    for (const pr of ((state.status && state.status.presets) || [])) {
      out.push({ title: `Apply Preset: ${pr.name}`, sub: pr.desc, badge: "PRESET", run: () => applyPresetById(pr.id) });
    }
    for (const sk of (state.skills || [])) {
      out.push({
        title: `${sk.enabled ? "Disable" : "Enable"} Skill: ${sk.name}`,
        sub: sk.category,
        badge: "SKILL",
        run: () => api("/api/skills/toggle", { id: sk.id, enabled: !sk.enabled }).then((r) => { if (r.ok) { state.skills = r.skills; renderSkills(); toast(`Updated ${sk.name}`); } }),
      });
    }
    for (const m of (state.modules || [])) {
      out.push({
        title: `Inspect Luau Module: ${m.id}.luau`,
        sub: `${m.category} · ${m.context}`,
        badge: "MODULE",
        run: () => { switchView("toolkit"); switchTkTab("modules"); openModuleModal(m); },
      });
    }
    return out;
  }

  let _paletteActions = [];
  function renderPalette(query) {
    const q = (query || "").trim().toLowerCase();
    const all = buildPaletteEntries();
    _paletteActions = q ? all.filter((x) => `${x.title} ${x.sub} ${x.badge}`.toLowerCase().includes(q)) : all.slice(0, 14);
    if (_paletteIndex >= _paletteActions.length) _paletteIndex = 0;
    $("#palette-results").innerHTML = _paletteActions.map((it, idx) => `
      <button class="pal-item ${idx === _paletteIndex ? "selected" : ""}" data-pal-idx="${idx}">
        <div>
          <div class="pal-item-title">${esc(it.title)}</div>
          <div class="pal-item-sub">${esc(it.sub)}</div>
        </div>
        <span class="tag accent">${esc(it.badge)}</span>
      </button>
    `).join("") || `<div class="sec-sub" style="padding:12px">No matching commands.</div>`;
  }

  // ── Logs Drawer ───────────────────────────────────────────────────────
  async function loadLogs() {
    const res = await api("/api/logs");
    if (!res || !res.ok) return;
    state.logs = res.logs || [];
    $("#logs-badge").textContent = String(state.logs.length);
    renderLogs();
  }

  function renderLogs() {
    const box = $("#logs-stream");
    if (!box || $("#logs-drawer").hidden) return;
    const q = ($("#logs-filter").value || "").trim().toLowerCase();
    const lines = q ? state.logs.filter((l) => l.msg.toLowerCase().includes(q)) : state.logs;
    box.innerHTML = lines.map((l) => `
      <div class="log-line">
        <span class="log-ts">${esc(l.ts)}</span>
        <span class="log-msg ${esc(l.color || "dim")}">${esc(l.msg)}</span>
      </div>
    `).join("");
    box.scrollTop = box.scrollHeight;
  }

  // ── Toolkit (60-Gate Luau Auditor, 19 Modules, Styles & Memory) ─────
  async function loadToolkitSummary(force = false) {
    if (state.tkLoaded && !force) return;
    try {
      const res = await api("/api/toolkit/summary");
      if (!res || !res.ok) return;
      state.tkLoaded = true;
      state.modules = res.modules || [];
      state.styles = res.styles || {};
      state.genres = res.genres || Object.keys(state.styles);
      if (state.genres.length && !state.styles[state.selectedGenre]) {
        state.selectedGenre = state.genres[0];
      }
      state.antiSlop = res.antiSlop || "";
      state.recovery = res.recovery || [];
      state.memory = res.memory || [];
      state.demoLuau = res.demoLuau || "";

      if ($("#audit-code-input") && !$("#audit-code-input").value.trim() && state.demoLuau) {
        $("#audit-code-input").value = state.demoLuau;
      }
      if ($("#tk-mod-count")) $("#tk-mod-count").textContent = String(state.modules.length);
      if ($("#tk-mem-count")) $("#tk-mem-count").textContent = String(state.memory.length);
      if ($("#antislop-body")) $("#antislop-body").textContent = state.antiSlop;

      renderModules();
      renderStylePills();
      renderStyleTokens();
      renderRecoveryList();
      renderMemoryList();
    } catch {}
  }

  function setAuditMode(mode) {
    state.auditMode = mode === "dir" ? "dir" : "code";
    $$("[data-audit-mode]").forEach((b) => b.classList.toggle("active", b.dataset.auditMode === state.auditMode));
    $("#audit-code-meta").hidden = state.auditMode === "dir";
    $("#audit-code-wrap").hidden = state.auditMode === "dir";
    $("#audit-dir-wrap").hidden = state.auditMode !== "dir";
  }

  async function runLuauAudit() {
    const payload = state.auditMode === "dir"
      ? { directory: ($("#audit-dir-input").value || "").trim() }
      : {
          code: $("#audit-code-input").value || "",
          filename: ($("#audit-filename").value || "").trim() || "Script.luau",
          context: $("#audit-context").value || "unknown",
        };
    toast("Running 60-gate Luau audit...");
    const res = await api("/api/toolkit/audit", payload);
    if (!res || !res.ok) {
      toast((res && res.error) || "Audit failed");
      return;
    }
    state.lastAudit = res;
    renderAuditResult(res);
    const sm = res.summary || {};
    toast(`Audit complete: ${sm.status} (${sm.total || 0} findings)`);
  }

  function renderAuditResult(res) {
    const sm = res.summary || {};
    $("#aud-status").textContent = sm.status || "PASS";
    $("#aud-mode-sub").textContent = res.filesScanned ? `${res.filesScanned} file(s) scanned` : `Mode: ${sm.mode || "default"}`;
    animateCount($("#aud-high"), sm.high || 0);
    animateCount($("#aud-med"), (sm.medium || 0) + (sm.low || 0));
    animateCount($("#aud-gates"), (sm.gates_triggered || []).length);
    $("#aud-lines-sub").textContent = `${sm.lines || 0} line(s) inspected`;

    const list = $("#audit-findings-list");
    const items = res.findings || [];
    if (!items.length) {
      list.innerHTML = `<div class="surface-card tk-card"><div class="sec-sub">✓ Clean! Zero findings triggered across all ${res.gateCount || 60} Aegis + Omni static gates.</div></div>`;
      return;
    }
    list.innerHTML = items.map((f) => {
      const p = f.priority || "medium";
      const tagCls = p === "high" ? "red" : (p === "medium" ? "amber" : "green");
      return `
        <div class="finding-row prio-${esc(p)}">
          <div class="finding-head">
            <div class="finding-left">
              <span class="tag ${tagCls}">${esc(p)} · ${esc(f.gate)}</span>
              <span class="finding-code">${esc(f.code)}</span>
            </div>
            <span class="finding-loc">${esc(f.path)}:${f.line}</span>
          </div>
          <div class="finding-msg">${esc(f.message)}</div>
        </div>
      `;
    }).join("");
  }

  function renderModules() {
    const grid = $("#modules-grid");
    if (!grid) return;
    const cat = state.modFilter || "All";
    const q = ($("#mod-search")?.value || "").trim().toLowerCase();
    const list = (state.modules || []).filter((m) => {
      if (cat !== "All" && (m.category || "").toLowerCase() !== cat.toLowerCase()) return false;
      if (q && !`${m.id} ${m.category} ${m.context} ${m.summary}`.toLowerCase().includes(q)) return false;
      return true;
    });
    grid.innerHTML = list.map((m) => `
      <div class="skill-card">
        <div class="skill-top">
          <span class="tag accent">${esc(m.category)}</span>
          <span class="tag">${esc(m.context)} · ${m.lines}L</span>
        </div>
        <h3 class="skill-title">${esc(m.id)}.luau</h3>
        <p class="skill-tagline">${esc(m.summary)}</p>
        <div class="skill-controls">
          <button class="btn-outline sm" data-preview-mod="${esc(m.id)}">PREVIEW</button>
          <div class="toolbar-actions">
            <button class="btn-outline sm" data-ai-mod="${esc(m.id)}" title="Copy AI prompt to fetch & wire this module">AI PROMPT</button>
            <button class="btn-primary sm" data-copy-mod="${esc(m.id)}">COPY</button>
          </div>
        </div>
      </div>
    `).join("") || `<div class="sec-sub">No matching Luau modules found.</div>`;
  }

  function openModuleModal(mod) {
    if (!mod) return;
    state.activeModule = mod;
    $("#mod-modal-eyebrow").textContent = `— ${String(mod.category || "LUAU MODULE").toUpperCase()} · ${String(mod.context || "SHARED").toUpperCase()}`;
    $("#mod-modal-title").textContent = `${mod.id}.luau`;
    $("#mod-modal-desc").textContent = mod.summary || "";
    $("#mod-modal-example").textContent = mod.example || "-- Require this ModuleScript cleanly from ReplicatedStorage or ServerScriptService";
    $("#mod-modal-code").textContent = mod.code || "";
    $("#module-modal").hidden = false;
  }

  async function runSkillRouterPreview(e) {
    if (e) e.preventDefault();
    const q = ($("#router-query").value || "").trim();
    if (!q) { toast("Enter a game task or feature first."); return; }
    const res = await api("/api/toolkit/route", { query: q, limit: 4 });
    if (!res || !res.ok) {
      toast((res && res.error) || "Routing failed");
      return;
    }
    state.lastRoute = res;
    renderRouterResults(res);
  }

  function renderRouterResults(res) {
    const box = $("#router-results");
    if (!box || !res) return;
    const skHtml = (res.skills || []).map((s) => `<span class="tag accent">${esc(s.id)} (${s.score})</span>`).join("");
    const stHtml = (res.styles || []).map((g) => `<span class="tag green">${esc(g)}</span>`).join("");
    const modHtml = (res.modules || []).map((m) => `<span class="tag">${esc(m.id)}.luau</span>`).join("");
    box.innerHTML = `
      <div class="router-chips"><span class="kpi-label">PLAYBOOKS:</span>${skHtml || '<span class="sec-sub">None</span>'}</div>
      ${stHtml ? `<div class="router-chips"><span class="kpi-label">STYLES:</span>${stHtml}</div>` : ""}
      ${modHtml ? `<div class="router-chips"><span class="kpi-label">MODULES:</span>${modHtml}</div>` : ""}
    `;
  }

  function renderStylePills() {
    const row = $("#style-genre-pills");
    if (!row) return;
    row.innerHTML = (state.genres || []).map((g) => `
      <button type="button" class="filter-pill ${g === state.selectedGenre ? "active" : ""}" data-style-genre="${esc(g)}">${esc(g)}</button>
    `).join("");
  }

  function renderStyleTokens() {
    const grid = $("#style-tokens-grid");
    if (!grid) return;
    const tokens = (state.styles && state.styles[state.selectedGenre]) || {};
    const entries = Object.entries(tokens);
    grid.innerHTML = entries.map(([k, v]) => `
      <div class="style-token">
        <div class="style-token-k">${esc(k.replace(/_/g, " "))}</div>
        <div class="style-token-v">${esc(v)}</div>
      </div>
    `).join("") || `<div class="sec-sub">No tokens loaded.</div>`;
  }

  function renderRecoveryList() {
    const box = $("#recovery-list");
    if (!box) return;
    const q = ($("#recovery-search")?.value || "").trim().toLowerCase();
    const list = (state.recovery || []).filter((r) => {
      if (!q) return true;
      return `${r.symptom} ${r.probe} ${r.repair} ${r.retest}`.toLowerCase().includes(q);
    });
    box.innerHTML = list.map((r, idx) => `
      <div class="recovery-card">
        <div class="recovery-head">
          <div class="recovery-title">${esc(r.symptom)}</div>
          <button type="button" class="btn-outline sm" data-copy-rec="${esc(r.symptom)}">DEBUG PROMPT</button>
        </div>
        <div class="recovery-step"><b>Probe:</b> ${esc(r.probe)}</div>
        <div class="recovery-step"><b>Repair:</b> ${esc(r.repair)}</div>
        <div class="recovery-step"><b>Retest:</b> ${esc(r.retest)}</div>
      </div>
    `).join("") || `<div class="sec-sub">No matching bug recovery recipes.</div>`;
  }

  function renderMemoryList() {
    const box = $("#memory-list");
    if (!box) return;
    if ($("#tk-mem-count")) $("#tk-mem-count").textContent = String((state.memory || []).length);
    const q = ($("#mem-search")?.value || "").trim().toLowerCase();
    const list = (state.memory || []).filter((r) => {
      if (!q) return true;
      return `${r.project} ${r.kind} ${r.key} ${r.value}`.toLowerCase().includes(q);
    });
    box.innerHTML = list.map((r) => `
      <div class="memory-row">
        <div class="skill-top">
          <div class="finding-left">
            <span class="tag accent">${esc(r.project)}</span>
            <span class="tag green">${esc(r.kind)} · rev ${r.revision}</span>
            <span class="finding-code">${esc(r.key)}</span>
          </div>
          <div class="toolbar-actions">
            <button type="button" class="btn-outline sm" data-copy-mem="${esc(r.id)}">COPY</button>
            <button type="button" class="btn-outline sm" data-del-mem="${esc(r.id)}">DEL</button>
          </div>
        </div>
        <div class="memory-val">${esc(r.value)}</div>
      </div>
    `).join("") || `<div class="sec-sub">No architecture memory entries saved yet. Add one on the left, or let any AI save verified decisions via <code>memory_write</code>.</div>`;
  }

  // ── Shared Actions ────────────────────────────────────────────────────
  async function refreshNow() {
    const btn = $("#btn-refresh-top");
    if (btn) btn.classList.add("is-spinning");
    toast("Refreshing Studio & MCP connections...");
    try {
      const res = await api("/api/refresh", {});
      renderStatus(res);
      toast("Connections refreshed.");
    } finally {
      if (btn) btn.classList.remove("is-spinning");
    }
  }

  async function applyPresetById(id) {
    const res = await api("/api/skills/preset", { preset: id });
    if (res && res.ok) {
      state.skills = res.skills || [];
      renderSkills();
      toast(`Applied preset: ${res.preset.name}`);
      tick();
    } else {
      toast((res && res.error) || "Preset failed");
    }
  }

  // ── Event Wiring ──────────────────────────────────────────────────────
  $$("#side-nav .nav-item").forEach((b) => b.addEventListener("click", () => switchView(b.dataset.view)));
  $$(".subtab").forEach((b) => b.addEventListener("click", () => switchSubtab(b.dataset.subtab)));

  $("#cta-browse-providers").addEventListener("click", () => { switchView("home"); switchSubtab("providers"); });
  $("#cta-open-skills").addEventListener("click", () => switchView("environment"));
  $("#quick-skills").addEventListener("click", () => switchView("environment"));
  $("#quick-toolkit").addEventListener("click", () => switchView("toolkit"));
  $("#quick-prompts").addEventListener("click", () => switchView("prompts"));
  $$(".tk-tab").forEach((b) => b.addEventListener("click", () => switchTkTab(b.dataset.tktab)));
  $$("[data-audit-mode]").forEach((b) => b.addEventListener("click", () => setAuditMode(b.dataset.auditMode)));
  $("#btn-run-audit").addEventListener("click", runLuauAudit);
  $("#btn-audit-demo").addEventListener("click", () => {
    setAuditMode("code");
    $("#audit-filename").value = "CombatHandler.server.luau";
    $("#audit-context").value = "server";
    $("#audit-code-input").value = state.demoLuau || "";
    runLuauAudit();
  });
  $("#btn-audit-clear").addEventListener("click", () => {
    $("#audit-code-input").value = "";
    $("#audit-dir-input").value = "";
    state.lastAudit = null;
    $("#aud-status").textContent = "READY";
    $("#aud-high").textContent = "0";
    $("#aud-med").textContent = "0";
    $("#aud-gates").textContent = "0";
    $("#aud-lines-sub").textContent = "0 lines inspected";
    $("#audit-findings-list").innerHTML = `<div class="surface-card tk-card"><div class="sec-sub">Cleared. Paste a Luau script or folder path and run the 60-gate audit.</div></div>`;
  });
  $("#btn-audit-fix-prompt").addEventListener("click", () => {
    const res = state.lastAudit;
    if (!res || !(res.findings || []).length) {
      toast("Run an audit with findings first.");
      return;
    }
    const bullets = res.findings.slice(0, 20).map((f) => `- [${f.priority.toUpperCase()} ${f.gate}] line ${f.line} (${f.code}): ${f.message}`).join("\n");
    const prompt = `Inspect and fix these ${res.findings.length} ZeroScript 60-Gate Luau Audit findings in ${res.filename} (${res.context} context), then re-run audit_luau to verify 0 findings remain:\n${bullets}`;
    copyText(prompt, "Copied AI Fix Prompt!");
  });

  $$("#mod-filters .filter-pill").forEach((b) => {
    b.addEventListener("click", () => {
      $$("#mod-filters .filter-pill").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      state.modFilter = b.dataset.mcat;
      renderModules();
    });
  });
  $("#mod-search").addEventListener("input", renderModules);
  $("#mod-modal-close").addEventListener("click", () => { $("#module-modal").hidden = true; });
  $("#mod-modal-done").addEventListener("click", () => { $("#module-modal").hidden = true; });
  $("#mod-modal-copy").addEventListener("click", () => {
    if (state.activeModule) copyText(state.activeModule.code || "", `Copied ${state.activeModule.id}.luau`);
  });
  $("#mod-modal-ai").addEventListener("click", () => {
    if (!state.activeModule) return;
    const m = state.activeModule;
    copyText(`Call {"command": "get_luau_module", "params": {"module_id": "${m.id}"}} first, install it into our project cleanly (${m.context}), and wire it up.`, `Copied AI prompt for ${m.id}.luau`);
  });

  $("#router-form").addEventListener("submit", runSkillRouterPreview);
  $("#btn-copy-routed-prompt").addEventListener("click", () => {
    const r = state.lastRoute;
    const q = ($("#router-query").value || "").trim();
    if (!r || !(r.skills || []).length) { toast("Run Route Task first."); return; }
    const skillsList = r.skills.map((s) => s.id).join(", ");
    const modsList = (r.modules || []).map((m) => m.id).join(", ");
    const stylesList = (r.styles || []).join(", ");
    const prompt = `Read these ZeroScript playbooks first: ${skillsList}.${stylesList ? ` Call get_style_guide for: ${stylesList}.` : ""}${modsList ? ` Pull starter modules via get_luau_module: ${modsList}.` : ""}\n\nTask: ${q}`;
    copyText(prompt, "Copied optimized AI prompt!");
  });
  $("#btn-copy-style-brief").addEventListener("click", () => {
    const g = state.selectedGenre;
    const tok = (state.styles && state.styles[g]) || {};
    const text = `Follow ZeroScript's ${g.toUpperCase()} Style Grammar:\n` + Object.entries(tok).map(([k, v]) => `- ${k}: ${v}`).join("\n");
    copyText(text, `Copied ${g} style brief!`);
  });
  $("#recovery-search").addEventListener("input", renderRecoveryList);

  $("#memory-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await api("/api/toolkit/memory/save", {
      project: ($("#mem-project").value || "").trim() || "default",
      key: $("#mem-key").value.trim(),
      kind: $("#mem-kind").value,
      state: $("#mem-state").value,
      value: $("#mem-value").value.trim(),
    });
    const msg = $("#mem-form-msg");
    if (res && res.ok) {
      msg.classList.remove("err");
      msg.textContent = `Saved rev ${res.record.revision}`;
      $("#mem-key").value = "";
      $("#mem-value").value = "";
      state.memory = res.records || [];
      renderMemoryList();
      tick();
      setTimeout(() => { msg.textContent = ""; }, 2500);
    } else {
      msg.classList.add("err");
      msg.textContent = (res && res.error) || "Save failed";
    }
  });
  $("#mem-search").addEventListener("input", renderMemoryList);
  $("#btn-clear-memory").addEventListener("click", async () => {
    const res = await api("/api/toolkit/memory/delete", { clear: true });
    if (res && res.ok) {
      state.memory = [];
      renderMemoryList();
      tick();
      toast("Project memory cleared.");
    }
  });
  $("#quick-activity").addEventListener("click", () => switchView("activity"));
  $("#quick-connections").addEventListener("click", () => { switchView("connections"); runDiagnostics(); });
  $("#guide-diag").addEventListener("click", () => { switchView("connections"); runDiagnostics(); });
  $("#guide-open-env").addEventListener("click", () => switchView("environment"));
  $("#guide-browse-ai").addEventListener("click", () => { switchView("home"); switchSubtab("providers"); });

  $("#btn-refresh-top").addEventListener("click", refreshNow);
  $("#btn-refresh-overview").addEventListener("click", refreshNow);
  $("#btn-overview-diag").addEventListener("click", () => { switchView("connections"); runDiagnostics(); });
  $("#btn-overview-ext").addEventListener("click", () => api("/api/open_folder", { folder: "extension" }));
  $("#btn-run-diag").addEventListener("click", runDiagnostics);
  $("#btn-copy-diag").addEventListener("click", () => {
    if (!state.diagnostics) { toast("Run Health Check first."); return; }
    const txt = (state.diagnostics.checks || [])
      .map((c) => `[${c.status.toUpperCase()}] ${c.title}: ${c.detail}`).join("\n");
    copyText(txt, "Diagnostic report copied.");
  });

  $("#btn-restart-top").addEventListener("click", async () => {
    toast("Restarting Roblox MCP proxy...");
    const res = await api("/api/restart_mcp", { server: "roblox" });
    if (res.ok) renderStatus(res);
    toast(res.ok ? "Roblox MCP restarted." : (res.error || "Restart failed"));
  });

  $("#btn-restart-all").addEventListener("click", async () => {
    toast("Restarting all MCP servers...");
    const res = await api("/api/restart_mcp", {});
    if (res.ok) renderStatus(res);
    toast(res.ok ? "All servers restarted." : (res.error || "Restart failed"));
  });

  $("#btn-clear-activity").addEventListener("click", async () => {
    const res = await api("/api/activity/clear", {});
    if (res && res.ok) {
      state.activity = { items: res.items || [], stats: res.stats || {} };
      renderActivity();
      toast("Activity timeline cleared.");
    }
  });

  $("#btn-open-palette").addEventListener("click", openPalette);
  $("#palette-input").addEventListener("input", (e) => { _paletteIndex = 0; renderPalette(e.target.value); });
  $("#palette-input").addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && _paletteActions.length) {
      e.preventDefault();
      _paletteIndex = (_paletteIndex + 1) % _paletteActions.length;
      renderPalette(e.target.value);
    } else if (e.key === "ArrowUp" && _paletteActions.length) {
      e.preventDefault();
      _paletteIndex = (_paletteIndex - 1 + _paletteActions.length) % _paletteActions.length;
      renderPalette(e.target.value);
    } else if (e.key === "Enter" && _paletteActions.length) {
      e.preventDefault();
      $("#cmd-palette").hidden = true;
      (_paletteActions[_paletteIndex] || _paletteActions[0]).run();
    }
  });
  for (const bId of ["#cmd-palette", "#skill-modal", "#module-modal", "#prompt-modal", "#logs-drawer"]) {
    $(bId).addEventListener("click", (e) => {
      if (e.target === e.currentTarget) e.currentTarget.hidden = true;
    });
  }
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if ($("#cmd-palette").hidden) openPalette();
      else $("#cmd-palette").hidden = true;
    } else if (e.key === "Escape") {
      $("#cmd-palette").hidden = true;
      $("#skill-modal").hidden = true;
      $("#module-modal").hidden = true;
      $("#prompt-modal").hidden = true;
      $("#logs-drawer").hidden = true;
    }
  });

  document.addEventListener("click", async (e) => {
    const pal = e.target.closest("[data-pal-idx]");
    if (pal) {
      const idx = Number(pal.dataset.palIdx);
      $("#cmd-palette").hidden = true;
      if (_paletteActions[idx]) _paletteActions[idx].run();
      return;
    }
    const urlBtn = e.target.closest("[data-url]");
    if (urlBtn) { await api("/api/open_url", { url: urlBtn.dataset.url }); return; }
    const folderBtn = e.target.closest("[data-folder]");
    if (folderBtn) { await api("/api/open_folder", { folder: folderBtn.dataset.folder }); return; }

    const favBtn = e.target.closest("[data-fav-prov]");
    if (favBtn) {
      const id = favBtn.dataset.favProv;
      const cur = new Set(((state.status && state.status.settings && state.status.settings.favoriteProviders) || []));
      if (cur.has(id)) cur.delete(id);
      else cur.add(id);
      const res = await api("/api/settings", { favoriteProviders: [...cur] });
      if (res && res.ok && state.status) {
        state.status.settings = res.settings;
        renderPinnedProviders(state.status.providers || [], res.settings.favoriteProviders || []);
        renderProviders(state.status.providers || [], res.settings.favoriteProviders || []);
      }
      return;
    }

    const presetBtn = e.target.closest("[data-preset]");
    if (presetBtn) { await applyPresetById(presetBtn.dataset.preset); return; }

    const copyAct = e.target.closest("[data-copy-act]");
    if (copyAct) {
      e.stopPropagation();
      const aid = Number(copyAct.dataset.copyAct);
      const item = (state.activity.items || []).find((x) => x.id === aid);
      if (item) {
        let parsedArgs = {};
        try { parsedArgs = JSON.parse(item.args || "{}"); } catch {}
        copyText(JSON.stringify({ command: item.tool, params: parsedArgs }, null, 2), `Copied ${item.tool} call`);
      }
      return;
    }

    const toggleAct = e.target.closest("[data-toggle-act]");
    if (toggleAct) {
      const aid = Number(toggleAct.dataset.toggleAct);
      if (state.expandedActs.has(aid)) state.expandedActs.delete(aid);
      else state.expandedActs.add(aid);
      const det = $(`#act-det-${aid}`);
      if (det) det.hidden = !state.expandedActs.has(aid);
      _sig.activity = "";
      return;
    }

    const restartSrv = e.target.closest("[data-restart-srv]");
    if (restartSrv) {
      const id = restartSrv.dataset.restartSrv;
      toast(`Restarting ${id}...`);
      const res = await api("/api/restart_mcp", { server: id });
      if (res.ok) renderStatus(res);
      toast(res.ok ? `${id} restarted.` : (res.error || "Restart failed"));
      return;
    }
    const removeSrv = e.target.closest("[data-remove-srv]");
    if (removeSrv) {
      const res = await api("/api/servers/remove", { server_id: removeSrv.dataset.removeSrv });
      if (res.ok) renderStatus(res);
      toast(res.ok ? "Server removed." : (res.error || "Remove failed"));
      return;
    }

    const modeBtn = e.target.closest("[data-skill-mode]");
    if (modeBtn) {
      const res = await api("/api/skills/toggle", { id: modeBtn.dataset.id, mode: modeBtn.dataset.skillMode });
      if (res.ok) { state.skills = res.skills; renderSkills(); toast("Skill mode updated."); }
      return;
    }
    const editSkill = e.target.closest("[data-edit-skill]");
    if (editSkill) {
      const sk = state.skills.find((x) => x.id === editSkill.dataset.editSkill);
      if (sk) openSkillModal(sk);
      return;
    }
    const expSkill = e.target.closest("[data-export-skill]");
    if (expSkill) {
      const sk = state.skills.find((x) => x.id === expSkill.dataset.exportSkill);
      if (sk) exportSkillMarkdown(sk);
      return;
    }
    const delSkill = e.target.closest("[data-del-skill]");
    if (delSkill) {
      const res = await api("/api/skills/delete", { id: delSkill.dataset.delSkill });
      if (res.ok) { state.skills = res.skills; renderSkills(); toast("Skill deleted."); }
      else toast(res.error || "Could not delete skill");
      return;
    }

    const copyStarter = e.target.closest("[data-copy-prompt]");
    if (copyStarter) {
      const idx = Number(copyStarter.dataset.copyPrompt);
      const list = (state.status && state.status.starterPrompts) || [];
      if (list[idx]) copyText(list[idx].text, "Prompt copied — paste into any AI chat!");
      return;
    }
    const copyCustom = e.target.closest("[data-copy-custom]");
    if (copyCustom) {
      const list = (state.status && state.status.settings && state.status.settings.customPrompts) || [];
      const item = list.find((x) => x.id === copyCustom.dataset.copyCustom);
      if (item) copyText(item.text, "Prompt copied!");
      return;
    }
    const delCustom = e.target.closest("[data-del-custom]");
    if (delCustom) {
      const res = await api("/api/prompts/delete", { id: delCustom.dataset.delCustom });
      if (res && res.ok && state.status) {
        state.status.settings = res.settings;
        renderPrompts(state.status.starterPrompts || [], res.customPrompts || []);
        toast("Prompt deleted.");
      }
      return;
    }

    const copyTool = e.target.closest("[data-copy-tool]");
    if (copyTool) {
      const name = copyTool.dataset.copyTool;
      copyText(`{"command": "${name}", "params": {}}`, `Copied ${name} snippet`);
      return;
    }

    const sw = e.target.closest("[data-accent-pick]");
    if (sw) {
      const accent = sw.dataset.accentPick;
      const res = await api("/api/settings", { accentTheme: accent });
      if (res && res.ok && state.status) state.status.settings = res.settings;
      applyTheme({ accentTheme: accent, liquidGlass: state.liquidGlass, liquidBackdrop: state.backdrop, glassStyle: state.glass, ambientMotion: state.motion });
      toast(`Accent theme: ${accent}`);
      return;
    }

    const bd = e.target.closest("[data-backdrop-pick]");
    if (bd) {
      const liquidBackdrop = bd.dataset.backdropPick;
      const res = await api("/api/settings", { liquidGlass: true, liquidBackdrop });
      if (res && res.ok && state.status) state.status.settings = res.settings;
      $("#set-liquid-glass").checked = true;
      applyTheme({ accentTheme: state.accent, liquidGlass: true, liquidBackdrop, glassStyle: state.glass, ambientMotion: state.motion });
      toast(`Liquid backdrop: ${liquidBackdrop}`);
      return;
    }

    const gs = e.target.closest("[data-glass-pick]");
    if (gs) {
      const glassStyle = gs.dataset.glassPick;
      const res = await api("/api/settings", { glassStyle });
      if (res && res.ok && state.status) state.status.settings = res.settings;
      applyTheme({ accentTheme: state.accent, liquidGlass: state.liquidGlass, liquidBackdrop: state.backdrop, glassStyle, ambientMotion: state.motion });
      toast(`Glass style: ${glassStyle}`);
      return;
    }

    const pMod = e.target.closest("[data-preview-mod]");
    if (pMod) {
      const m = (state.modules || []).find((x) => x.id === pMod.dataset.previewMod);
      if (m) openModuleModal(m);
      return;
    }
    const cMod = e.target.closest("[data-copy-mod]");
    if (cMod) {
      const m = (state.modules || []).find((x) => x.id === cMod.dataset.copyMod);
      if (m) copyText(m.code || "", `Copied ${m.id}.luau`);
      return;
    }
    const aiMod = e.target.closest("[data-ai-mod]");
    if (aiMod) {
      const m = (state.modules || []).find((x) => x.id === aiMod.dataset.aiMod);
      if (m) copyText(`Call {"command": "get_luau_module", "params": {"module_id": "${m.id}"}} first, install it cleanly (${m.context}), and wire it into the project.`, `Copied AI prompt for ${m.id}.luau`);
      return;
    }

    const sgBtn = e.target.closest("[data-style-genre]");
    if (sgBtn) {
      state.selectedGenre = sgBtn.dataset.styleGenre;
      renderStylePills();
      renderStyleTokens();
      return;
    }

    const recBtn = e.target.closest("[data-copy-rec]");
    if (recBtn) {
      const sym = recBtn.dataset.copyRec;
      copyText(`Call {"command": "diagnose_bug", "params": {"query": "${sym}"}} first, then follow Probe -> Repair -> Retest against our live Studio place.`, `Copied debug prompt for '${sym}'`);
      return;
    }

    const cMem = e.target.closest("[data-copy-mem]");
    if (cMem) {
      const item = (state.memory || []).find((x) => x.id === cMem.dataset.copyMem);
      if (item) copyText(`[${item.project}] (${item.kind}) ${item.key}: ${item.value}`, "Memory entry copied.");
      return;
    }
    const dMem = e.target.closest("[data-del-mem]");
    if (dMem) {
      const res = await api("/api/toolkit/memory/delete", { id: dMem.dataset.delMem });
      if (res && res.ok) {
        state.memory = res.records || [];
        renderMemoryList();
        tick();
        toast("Memory entry deleted.");
      }
      return;
    }
  });

  document.addEventListener("change", async (e) => {
    const toggle = e.target.closest("[data-toggle-skill]");
    if (toggle) {
      const res = await api("/api/skills/toggle", { id: toggle.dataset.toggleSkill, enabled: toggle.checked });
      if (res.ok) { state.skills = res.skills; renderSkills(); tick(); }
    }
  });

  // Filters & searches
  $$("#prov-filters .filter-pill").forEach((b) => {
    b.addEventListener("click", () => {
      $$("#prov-filters .filter-pill").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      state.provFilter = b.dataset.pcat;
      if (state.status) renderProviders(state.status.providers || [], (state.status.settings && state.status.settings.favoriteProviders) || []);
    });
  });
  $("#prov-search").addEventListener("input", () => {
    if (state.status) renderProviders(state.status.providers || [], (state.status.settings && state.status.settings.favoriteProviders) || []);
  });

  $$("#activity-filters .filter-pill").forEach((b) => {
    b.addEventListener("click", () => {
      $$("#activity-filters .filter-pill").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      state.actFilter = b.dataset.af;
      renderActivity();
    });
  });
  $("#btn-export-activity").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(state.activity, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `zeroscript-activity-${Date.now()}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    toast("Activity exported as JSON.");
  });
  $("#activity-search").addEventListener("input", renderActivity);

  $("#set-liquid-glass").addEventListener("change", async (e) => {
    const liquidGlass = e.target.checked;
    const res = await api("/api/settings", { liquidGlass });
    if (res && res.ok && state.status) state.status.settings = res.settings;
    applyTheme({ accentTheme: state.accent, liquidGlass, liquidBackdrop: state.backdrop, glassStyle: state.glass, ambientMotion: state.motion });
    toast(`Liquid Glass ${liquidGlass ? "enabled" : "disabled"}.`);
  });

  $$("#skill-filters .filter-pill").forEach((b) => {
    b.addEventListener("click", () => {
      $$("#skill-filters .filter-pill").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      state.skillFilter = b.dataset.cat;
      renderSkills();
    });
  });
  $("#skill-search").addEventListener("input", renderSkills);

  // Import Markdown Skill
  $("#btn-import-skill").addEventListener("click", () => $("#skill-import-file").click());
  $("#skill-import-file").addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const raw = await file.text();
    const baseName = file.name.replace(/\.(md|markdown|txt)$/i, "");
    let name = baseName, category = "Custom", tagline = "", mode = "auto", content = raw.trim();
    if (raw.startsWith("---\n")) {
      const end = raw.indexOf("\n---\n", 4);
      if (end !== -1) {
        const fm = raw.slice(4, end);
        content = raw.slice(end + 5).trim();
        for (const line of fm.split("\n")) {
          const i = line.indexOf(":");
          if (i === -1) continue;
          const k = line.slice(0, i).trim().toLowerCase();
          const v = line.slice(i + 1).trim().replace(/^["']|["']$/g, "");
          if (k === "name" && v) name = v;
          if (k === "category" && v) category = v;
          if (k === "tagline" && v) tagline = v;
          if (k === "mode" && (v === "auto" || v === "always")) mode = v;
        }
      }
    }
    const res = await api("/api/skills/save", { name, category, tagline, mode, content });
    e.target.value = "";
    if (res && res.ok) {
      state.skills = res.skills || [];
      renderSkills();
      toast(`Imported skill: ${res.skill.name}`);
    } else {
      toast((res && res.error) || "Import failed");
    }
  });

  // Modals
  $("#btn-new-skill").addEventListener("click", () => openSkillModal(null));
  $("#skill-modal-close").addEventListener("click", () => { $("#skill-modal").hidden = true; });
  $("#skill-modal-cancel").addEventListener("click", () => { $("#skill-modal").hidden = true; });
  $("#skill-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await api("/api/skills/save", {
      id: $("#sk-id").value.trim() || state.editingId,
      name: $("#sk-name").value.trim(),
      category: $("#sk-cat").value,
      mode: $("#sk-mode").value,
      tagline: $("#sk-tagline").value.trim(),
      content: $("#sk-content").value,
    });
    if (res.ok) {
      state.skills = res.skills;
      renderSkills();
      $("#skill-modal").hidden = true;
      toast("Skill saved and synced to extensions.");
    } else {
      $("#skill-form-msg").textContent = res.error || "Failed to save";
      $("#skill-form-msg").classList.add("err");
    }
  });

  $("#btn-new-prompt").addEventListener("click", () => {
    $("#pr-title").value = "";
    $("#pr-cat").value = "Custom";
    $("#pr-text").value = "";
    $("#prompt-form-msg").textContent = "";
    $("#prompt-modal").hidden = false;
  });
  $("#prompt-modal-close").addEventListener("click", () => { $("#prompt-modal").hidden = true; });
  $("#prompt-modal-cancel").addEventListener("click", () => { $("#prompt-modal").hidden = true; });
  $("#prompt-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await api("/api/prompts/save", {
      title: $("#pr-title").value.trim(),
      category: $("#pr-cat").value.trim() || "Custom",
      text: $("#pr-text").value,
    });
    if (res && res.ok) {
      if (state.status) state.status.settings = res.settings;
      renderPrompts((state.status && state.status.starterPrompts) || [], res.customPrompts || []);
      $("#prompt-modal").hidden = true;
      toast("Prompt saved to library.");
    } else {
      $("#prompt-form-msg").textContent = (res && res.error) || "Failed to save";
    }
  });

  // Global Prompt Form
  $("#global-prompt-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await api("/api/settings", { globalPrompt: $("#global-prompt-input").value });
    if (res && res.ok) {
      if (state.status) state.status.settings = res.settings;
      $("#global-prompt-msg").textContent = "Synced to all 12 AIs.";
      toast("Global instructions synced.");
      setTimeout(() => { $("#global-prompt-msg").textContent = ""; }, 2600);
    }
  });
  $("#btn-clear-global-prompt").addEventListener("click", async () => {
    $("#global-prompt-input").value = "";
    const res = await api("/api/settings", { globalPrompt: "" });
    if (res && res.ok && state.status) state.status.settings = res.settings;
    toast("Global instructions cleared.");
  });

  // Add MCP Server Form
  $("#add-server-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("#add-server-msg");
    msg.classList.remove("err");
    msg.textContent = "Connecting...";
    let env = null;
    const rawEnv = $("#srv-env").value.trim();
    if (rawEnv) {
      try { env = JSON.parse(rawEnv); } catch {
        msg.textContent = "Invalid Env JSON";
        msg.classList.add("err");
        return;
      }
    }
    const res = await api("/api/servers/add", {
      server_id: $("#srv-id").value.trim(),
      command: $("#srv-cmd").value.trim(),
      args: $("#srv-args").value.trim(),
      env,
    });
    if (res.ok) {
      renderStatus(res);
      $("#add-server-form").reset();
      msg.textContent = "Server connected.";
    } else {
      msg.textContent = res.error || "Failed to add server";
      msg.classList.add("err");
    }
  });

  $("#tool-search").addEventListener("input", () => {
    if (state.status) renderConnections(state.status.servers || [], state.status.tools || []);
  });

  // Settings Form
  $("#settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await api("/api/settings", {
      userName: $("#set-username").value.trim(),
      liquidGlass: $("#set-liquid-glass").checked,
      liquidBackdrop: state.backdrop,
      glassStyle: state.glass,
      ambientMotion: $("#set-motion").checked,
      minimizeToTray: $("#set-tray").checked,
      autoOpenWindow: $("#set-autoopen").checked,
      accentTheme: state.accent,
    });
    if (res.ok) {
      if (state.status) state.status.settings = res.settings;
      renderStatus(state.status);
      $("#settings-msg").textContent = "Saved.";
      toast("Preferences saved.");
      setTimeout(() => { $("#settings-msg").textContent = ""; }, 2400);
    }
  });

  $("#btn-open-logs").addEventListener("click", () => { $("#logs-drawer").hidden = false; loadLogs(); });
  $("#btn-close-logs").addEventListener("click", () => { $("#logs-drawer").hidden = true; });
  $("#logs-filter").addEventListener("input", renderLogs);
  $("#btn-copy-logs").addEventListener("click", () => {
    const text = state.logs.map((l) => `${l.ts} ${l.msg}`).join("\n");
    copyText(text, "Logs copied.");
  });

  async function quitApp() {
    await api("/api/quit", {});
    toast("ZeroScript stopped.");
    setTimeout(() => window.close(), 300);
  }
  $("#btn-quit-side").addEventListener("click", quitApp);
  $("#btn-quit-settings").addEventListener("click", quitApp);

  // ── Boot & Polling ────────────────────────────────────────────────────
  async function tick() {
    try {
      const s = await api("/api/status");
      renderStatus(s);
      await loadLogs();
      if ($("#view-activity").classList.contains("active")) await loadActivity();
    } catch {}
  }

  startAmbientCanvas();
  startPointerSheen();
  tick();
  loadSkills();
  loadToolkitSummary();
  setInterval(tick, 2500);
})();
