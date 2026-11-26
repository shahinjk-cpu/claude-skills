/* ============================================================
 * screen.js — 页面装配：缩放、时钟、KPI、滚动表、播报、交互
 * ============================================================ */
(function (global) {
  "use strict";

  var D = global.DashboardData;
  var F = global.DashboardFormat;
  var reduced = (global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches)
    || /[?&]static=1/.test(global.location.search);   // ?static=1：截图/打印用，禁用动画

  /* ---------- 1. 1920×1080 等比缩放 ---------- */
  function fitStage() {
    var stage = document.getElementById("stage");
    if (!stage) return;
    var w = global.innerWidth;
    var h = global.innerHeight;
    var s = Math.min(w / 1920, h / 1080);
    stage.style.setProperty("--s", s.toFixed(4));
  }

  /* ---------- 2. 时钟 ---------- */
  var WEEK = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
  function tickClock() {
    var d = new Date();
    var dateEl = document.getElementById("date-text");
    var timeEl = document.getElementById("time-text");
    if (dateEl) dateEl.textContent = d.getFullYear() + "年" + (d.getMonth() + 1) + "月" + d.getDate() + "日 " + WEEK[d.getDay()];
    if (timeEl) timeEl.textContent = F.time(d);
  }

  /* ---------- 3. KPI 绑定 + 数字滚动 ---------- */
  var lastValues = Object.create(null);

  function animateNumber(el, target, formatter) {
    var key = el.getAttribute("data-bind") || el.id || "anon";
    var from = Number(lastValues[key] || 0);
    var to = Number(target || 0);
    lastValues[key] = to;
    if (reduced || from === to) { el.textContent = formatter(to); return; }
    var start = performance.now();
    var dur = 900;
    function frame(now) {
      var p = Math.min(1, (now - start) / dur);
      var e = 1 - Math.pow(1 - p, 3);
      el.textContent = formatter(from + (to - from) * e);
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function bindKpis() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-bind]"), function (el) {
      var path = el.getAttribute("data-bind");
      var format = el.getAttribute("data-format") || "raw";
      var value = D.get(path, null);
      if (value === null) { el.textContent = "--"; return; }

      if (format === "raw") {
        el.textContent = value;
      } else if (format.indexOf("pct") === 0 && Number(value) < 0) {
        el.classList.add("is-down");
        animateNumber(el, Math.abs(Number(value)), function (n) { return "-" + n.toFixed(format === "pct1" ? 1 : 0) + "%"; });
      } else if (F[format]) {
        animateNumber(el, value, F[format]);
      } else {
        el.textContent = value;
      }
    });
  }

  /* ---------- 4. 实时工单滚动 ---------- */
  var ticketTimer = null;

  function statusTag(status) {
    var map = {
      "已办结": "s-done",
      "处置中": "s-doing",
      "待派单": "s-warn",
      "已升级": "s-danger"
    };
    return '<span class="tag ' + (map[status] || "s-doing") + '">' + status + "</span>";
  }

  function renderTickets(rows) {
    var track = document.getElementById("ticket-track");
    if (!track) return;
    rows = (rows || []).slice(0, 20);
    track.innerHTML = rows.map(function (r) {
      return '<div class="ticket-row">' +
        '<span class="t">' + (r.time || "--:--") + "</span>" +
        '<span class="t2" title="' + (r.title || "") + '">' + (r.title || "") + "</span>" +
        '<span class="area">' + (r.area || "") + "</span>" +
        statusTag(r.status) +
        "</div>";
    }).join("");
    startTicketScroll();
  }

  function startTicketScroll() {
    clearInterval(ticketTimer);
    var viewport = document.querySelector(".ticket-viewport");
    var track = document.getElementById("ticket-track");
    if (!viewport || !track || reduced) return;
    var rowH = 32;
    var visible = Math.floor(viewport.clientHeight / rowH);
    if (track.children.length <= visible) return;

    var offset = 0;
    ticketTimer = setInterval(function () {
      if (document.hidden) return;
      offset += rowH;
      track.style.transition = "transform .55s cubic-bezier(.22,.61,.36,1)";
      track.style.transform = "translateY(-" + offset + "px)";
      setTimeout(function () {
        var first = track.firstElementChild;
        if (!first) return;
        track.style.transition = "none";
        track.appendChild(first);
        offset = 0;
        track.style.transform = "translateY(0)";
        void track.offsetHeight;
      }, 570);
    }, 2800);
  }

  /* ---------- 5. 预警列表 ---------- */
  function renderAlerts(items) {
    var ul = document.getElementById("alert-list");
    if (!ul) return;
    ul.innerHTML = (items || []).slice(0, 3).map(function (a) {
      return '<li class="alert-item" data-level="' + (a.level || "major") + '">' +
        '<i class="bar"></i>' +
        '<div class="alert-main">' +
        '<p class="alert-title" title="' + (a.title || "") + '">' + (a.title || "") + "</p>" +
        '<p class="alert-sub">' + (a.area || "") + " · " + (a.type || "") + "</p>" +
        "</div>" +
        '<span class="alert-time">' + (a.time || "") + "</span>" +
        "</li>";
    }).join("");
  }

  /* ---------- 6. 底部播报 ---------- */
  function renderTicker(items) {
    var track = document.getElementById("ticker-track");
    if (!track || !items || !items.length) return;
    var html = items.map(function (t) { return "<span>" + t + "</span>"; }).join("");
    track.innerHTML = html + html; // 复制一份实现无缝
    startMarquee(track);
  }

  var marqueeRaf = null;
  function startMarquee(track) {
    if (marqueeRaf) cancelAnimationFrame(marqueeRaf);
    if (reduced) return;
    var x = 0;
    var half = 0;
    var last = performance.now();
    var paused = false;

    track.parentElement.addEventListener("mouseenter", function () { paused = true; });
    track.parentElement.addEventListener("mouseleave", function () { paused = false; });

    function step(now) {
      var dt = Math.min(64, now - last);
      last = now;
      if (!paused && !document.hidden) {
        if (!half) half = track.scrollWidth / 2;
        x += dt * 0.045;
        if (half && x >= half) x -= half;
        track.style.transform = "translateX(" + (-x) + "px)";
      }
      marqueeRaf = requestAnimationFrame(step);
    }
    marqueeRaf = requestAnimationFrame(step);
  }

  /* ---------- 7. 状态灯 ---------- */
  var STATE_TEXT = {
    live: "实时数据",
    mock: "示例数据",
    loading: "连接中",
    stale: "数据延迟",
    error: "连接失败",
    idle: "未连接"
  };

  function applyStatus(s) {
    var dot = document.getElementById("data-dot");
    var label = document.getElementById("data-state");
    var modeEl = document.getElementById("mode-text");
    if (dot) dot.setAttribute("data-state", s.status);
    if (label) label.textContent = STATE_TEXT[s.status] || s.status;
    if (modeEl) modeEl.textContent = String(s.mode || "").toUpperCase();
    var refreshEl = document.getElementById("refresh-text");
    if (refreshEl && s.updatedAt) refreshEl.textContent = F.time(s.updatedAt);
    var mapUpd = document.getElementById("map-updated");
    if (mapUpd && s.updatedAt) mapUpd.textContent = "更新于 " + F.time(s.updatedAt);
  }

  /* ---------- 8. 导航 / 全屏 ---------- */
  function bindNav() {
    Array.prototype.forEach.call(document.querySelectorAll(".nav-item"), function (btn) {
      btn.addEventListener("click", function () {
        Array.prototype.forEach.call(document.querySelectorAll(".nav-item"), function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        global.DashboardCharts.setView(btn.getAttribute("data-view"));
      });
    });
  }

  function bindFullscreen() {
    var btn = document.getElementById("btn-fullscreen");
    if (!btn) return;
    btn.addEventListener("click", function () {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen && document.documentElement.requestFullscreen();
      } else {
        document.exitFullscreen && document.exitFullscreen();
      }
    });
  }

  /* ---------- 9. 启动 ---------- */
  function onData(payload) {
    applyStatus(payload.status);
    bindKpis();
    renderTickets(D.get("lists.tickets"));
    renderAlerts(D.get("alerts"));
    renderTicker(D.get("ticker"));
  }

  function boot() {
    fitStage();
    global.addEventListener("resize", fitStage);
    tickClock();
    setInterval(tickClock, 1000);

    bindNav();
    bindFullscreen();

    D.on("data", onData);
    D.on("status", applyStatus);
    D.start();

    global.DashboardCharts.init();

    // 首次进入的轻微入场
    document.querySelector(".grid").classList.add("view-enter");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(window);
