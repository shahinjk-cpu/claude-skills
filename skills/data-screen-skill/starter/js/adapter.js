/* ============================================================
 * adapter.js — 大屏外部数据适配层（无依赖）
 * ------------------------------------------------------------
 * 设计原则：
 *  1. 图表代码永远不直接 fetch / WebSocket，只订阅 DashboardData。
 *  2. 所有数据源都归一到同一个 snapshot 结构（见 data-contract.md）。
 *  3. 失败时保留上一帧数据并标记 stale，绝不白屏。
 *  4. 只依赖浏览器标准 API，可被任意框架/Agent 复用。
 * ============================================================ */
(function (global) {
  "use strict";

  var DEFAULTS = {
    mode: "mock",              // mock | rest | sse | ws | inline | postMessage
    endpoint: "./data/mock.json",
    pollInterval: 30000,
    timeout: 8000,
    retry: 3,
    retryBaseDelay: 1500,
    headers: {},
    withCredentials: false,
    transform: null,
    staleAfter: 120000,        // 超过该时长未更新则标记 stale
    debug: false
  };

  var listeners = { data: [], status: [] };
  var state = {
    snapshot: null,
    status: "idle",            // idle | loading | live | mock | stale | error
    error: null,
    updatedAt: 0,
    lastAttemptAt: 0,
    failures: 0,
    mode: "mock"
  };
  var config = {};
  var pollTimer = null;
  var abortCtl = null;
  var source = null;           // EventSource / WebSocket
  var destroyed = false;

  function log() {
    if (!config.debug) return;
    var args = Array.prototype.slice.call(arguments);
    args.unshift("[dashboard-data]");
    console.log.apply(console, args);
  }

  function emit(type, payload) {
    var list = listeners[type] || [];
    for (var i = 0; i < list.length; i++) {
      try { list[i](payload); } catch (e) { console.error("[dashboard-data] listener error", e); }
    }
    var evtName = type === "data" ? "dashboard:data" : "dashboard:status";
    try {
      global.dispatchEvent(new CustomEvent(evtName, { detail: payload }));
    } catch (e) { /* 老浏览器忽略 */ }
  }

  function setStatus(next, error) {
    var changed = state.status !== next || error !== state.error;
    state.status = next;
    state.error = error || null;
    if (changed) emit("status", getStatus());
  }

  function getStatus() {
    return {
      status: state.status,
      error: state.error,
      updatedAt: state.updatedAt,
      mode: state.mode,
      failures: state.failures
    };
  }

  /* ---------- 路径取值：支持 "kpis.events.value" 与 "series.trend.data[0]" ---------- */
  function get(path, fallback) {
    if (!state.snapshot || !path) return fallback;
    var cur = state.snapshot;
    var parts = String(path).replace(/\[(\d+)\]/g, ".$1").split(".").filter(Boolean);
    for (var i = 0; i < parts.length; i++) {
      if (cur == null) return fallback;
      cur = cur[parts[i]];
    }
    return cur === undefined || cur === null ? fallback : cur;
  }

  /* ---------- 数据校验：只警告，不阻塞渲染 ---------- */
  function validate(data) {
    if (!data || typeof data !== "object") return ["payload is not an object"];
    var problems = [];
    if (!data.meta) problems.push("missing meta");
    if (!Array.isArray(data.kpis) && !data.kpis) problems.push("missing kpis");
    if (!data.series && !data.lists && !data.geo) problems.push("missing series/lists/geo");
    if (problems.length) log("payload warnings:", problems.join(", "));
    return problems;
  }

  function applyTransform(raw) {
    if (!config.transform) return raw;
    var fn = typeof config.transform === "function"
      ? config.transform
      : global.DashboardTransforms && global.DashboardTransforms[config.transform];
    if (typeof fn !== "function") {
      console.warn("[dashboard-data] transform not found:", config.transform);
      return raw;
    }
    return fn(raw);
  }

  function commit(raw) {
    var data = applyTransform(raw);
    validate(data);
    state.snapshot = data;
    state.updatedAt = Date.now();
    state.failures = 0;
    setStatus(config.mode === "mock" ? "mock" : "live");
    emit("data", { snapshot: data, status: getStatus() });
    if (config.mode !== "mock") {
      try {
        global.localStorage.setItem("dashboard:last:" + location.pathname, JSON.stringify(data));
      } catch (e) { /* 隐私模式忽略 */ }
    }
    return data;
  }

  function fail(err) {
    state.failures += 1;
    var msg = (err && (err.message || err.type)) || String(err);
    console.warn("[dashboard-data] load failed:", msg);
    // 优先使用上一帧；其次使用上次成功缓存（离线重启兜底）
    if (!state.snapshot) {
      try {
        var cached = global.localStorage.getItem("dashboard:last:" + location.pathname);
        if (cached) {
          state.snapshot = JSON.parse(cached);
          log("restored last snapshot from localStorage");
        }
      } catch (e) { /* ignore */ }
    }
    setStatus(state.snapshot ? "stale" : "error", msg);
    return state.snapshot;
  }

  /* ---------- 1. 静态 JSON / REST ---------- */
  function fetchJson(url, options, attempt) {
    attempt = attempt || 0;
    if (abortCtl) abortCtl.abort();
    abortCtl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = null;

    var opts = {
      method: "GET",
      headers: Object.assign({ Accept: "application/json" }, config.headers || {}),
      credentials: config.withCredentials ? "include" : "same-origin"
    };
    if (abortCtl) opts.signal = abortCtl.signal;

    if (config.timeout > 0) {
      timer = setTimeout(function () {
        if (abortCtl) abortCtl.abort();
      }, config.timeout);
    }

    return fetch(url, opts).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status + " " + res.statusText);
      var ct = res.headers.get("content-type") || "";
      return ct.indexOf("json") >= 0 ? res.json() : res.text().then(function (t) { return JSON.parse(t); });
    }).then(function (json) {
      clearTimeout(timer);
      return json;
    }).catch(function (err) {
      clearTimeout(timer);
      if (attempt < config.retry && !destroyed) {
        var delay = config.retryBaseDelay * Math.pow(2, attempt);
        log("retry in " + delay + "ms", err.message);
        return new Promise(function (resolve) { setTimeout(resolve, delay); }).then(function () {
          return fetchJson(url, options, attempt + 1);
        });
      }
      throw err;
    });
  }

  /* ---------- 2. SSE ---------- */
  function connectSse(url) {
    if (typeof EventSource === "undefined") throw new Error("EventSource unsupported");
    source = new EventSource(url, { withCredentials: !!config.withCredentials });
    source.onmessage = function (evt) {
      try { commit(JSON.parse(evt.data)); } catch (e) { console.warn("[dashboard-data] bad SSE message", e); }
    };
    source.onerror = function () { fail(new Error("SSE disconnected")); };
    log("SSE connected", url);
  }

  /* ---------- 3. WebSocket ---------- */
  function connectWs(url) {
    source = new WebSocket(url);
    source.onopen = function () { log("WS connected", url); state.failures = 0; };
    source.onmessage = function (evt) {
      try { commit(JSON.parse(evt.data)); } catch (e) { console.warn("[dashboard-data] bad WS message", e); }
    };
    source.onerror = function () { fail(new Error("WS error")); };
    source.onclose = function () {
      if (destroyed) return;
      fail(new Error("WS closed"));
      setTimeout(function () { if (!destroyed) connectWs(url); }, Math.min(15000, config.retryBaseDelay * Math.pow(2, state.failures)));
    };
  }

  /* ---------- 4. 父窗口推送（iframe 嵌入） ---------- */
  function bindPostMessage() {
    global.addEventListener("message", function (evt) {
      // 生产环境请校验 evt.origin，例如：if (evt.origin !== "https://your-portal.example") return;
      var d = evt.data;
      if (!d) return;
      if (d.type === "dashboard:data" && d.payload) commit(d.payload);
      if (d.type === "dashboard:config" && d.payload) Object.assign(config, d.payload);
    });
    // 主动告诉父窗口已就绪
    try { if (global.parent !== global) global.parent.postMessage({ type: "dashboard:ready" }, "*"); } catch (e) {}
  }

  function schedulePoll() {
    clearTimeout(pollTimer);
    if (!config.pollInterval || config.pollInterval <= 0 || config.mode === "mock" || destroyed) return;
    pollTimer = setTimeout(function () { refresh(); }, config.pollInterval);
  }

  function refresh() {
    if (destroyed) return;
    state.lastAttemptAt = Date.now();
    if (!state.snapshot) setStatus("loading");
    if (config.mode === "mock" || config.mode === "rest") {
      fetchJson(config.endpoint).then(function (raw) {
        commit(raw);
        schedulePoll();
      }).catch(function (err) {
        fail(err);
        schedulePoll();
      });
    } else {
      schedulePoll();
    }
  }

  function start() {
    config = Object.assign({}, DEFAULTS, global.DASHBOARD_CONFIG || {});
    state.mode = config.mode;

    if (config.mode === "inline") {
      commit(global.DASHBOARD_DATA || {});
      return;
    }
    if (config.mode === "postMessage") {
      bindPostMessage();
      setStatus("loading");
      return;
    }
    if (config.mode === "sse") {
      try { connectSse(config.endpoint); setStatus("loading"); } catch (e) { fail(e); }
      return;
    }
    if (config.mode === "ws") {
      connectWs(config.endpoint);
      setStatus("loading");
      return;
    }
    refresh();
  }

  function destroy() {
    destroyed = true;
    clearTimeout(pollTimer);
    if (abortCtl) abortCtl.abort();
    if (source && source.close) source.close();
  }

  function on(type, fn) {
    (listeners[type] = listeners[type] || []).push(fn);
    return function off() {
      var i = listeners[type].indexOf(fn);
      if (i >= 0) listeners[type].splice(i, 1);
    };
  }

  /* ---------- 格式化工具 ---------- */
  var fmt = {
    int: function (n) { return Number(n || 0).toLocaleString("zh-CN", { maximumFractionDigits: 0 }); },
    dec1: function (n) { return Number(n || 0).toLocaleString("zh-CN", { minimumFractionDigits: 1, maximumFractionDigits: 1 }); },
    pct: function (n) { var v = Number(n || 0); return (v > 0 ? "+" : "") + v.toFixed(0) + "%"; },
    pct1: function (n) { var v = Number(n || 0); return (v > 0 ? "+" : "") + v.toFixed(1) + "%"; },
    min: function (n) { return Number(n || 0).toFixed(0); },
    wan: function (n) { return (Number(n || 0) / 10000).toFixed(1) + " 万"; },
    money: function (n) { return "¥" + Number(n || 0).toLocaleString("zh-CN", { maximumFractionDigits: 0 }); },
    time: function (d) {
      var t = d instanceof Date ? d : new Date(d);
      if (isNaN(t)) return "--";
      return String(t.getHours()).padStart(2, "0") + ":" + String(t.getMinutes()).padStart(2, "0") + ":" + String(t.getSeconds()).padStart(2, "0");
    }
  };

  global.DashboardData = {
    start: start,
    refresh: refresh,
    destroy: destroy,
    on: on,
    get: get,
    format: fmt,
    get snapshot() { return state.snapshot; },
    get status() { return getStatus(); },
    get config() { return config; }
  };
  global.DashboardFormat = fmt;
})(window);
