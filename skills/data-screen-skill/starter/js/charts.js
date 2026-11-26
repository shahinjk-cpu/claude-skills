/* ============================================================
 * charts.js — ECharts 图表工厂
 * 每个图表只接收「已归一化」的数据，不关心数据来自哪里。
 * 新增图表：写一个 builder，再在 REGISTRY 注册即可。
 * ============================================================ */
(function (global) {
  "use strict";

  var echarts = global.echarts;
  var charts = {};
  var observers = [];
  var theme = null;
  var currentView = "overview";

  function cssVar(name, fallback) {
    var v = getComputedStyle(document.body).getPropertyValue(name).trim();
    return v || fallback;
  }

  function readTheme() {
    return {
      accent: cssVar("--c-accent", "#35d6ff"),
      accent2: cssVar("--c-accent-2", "#2e7bff"),
      warm: cssVar("--c-warm", "#ffc93c"),
      warn: cssVar("--c-warn", "#ff8a3d"),
      danger: cssVar("--c-danger", "#ff4d6d"),
      ok: cssVar("--c-ok", "#2fe6a8"),
      text: cssVar("--c-text", "#e8f3ff"),
      dim: cssVar("--c-dim", "#7d95b5"),
      faint: cssVar("--c-faint", "#4a6285"),
      line: cssVar("--c-line", "rgba(74,158,255,.18)")
    };
  }

  function alpha(hex, a) {
    var h = (hex || "").replace("#", "");
    if (h.length === 3) h = h.replace(/(.)/g, "$1$1");
    var n = parseInt(h, 16);
    if (isNaN(n)) return "rgba(53,214,255," + a + ")";
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }

  function vGrad(c1, c2) {
    return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: c1 },
      { offset: 1, color: c2 }
    ]);
  }

  var baseTooltip = function () {
    return {
      backgroundColor: "rgba(4,14,28,.94)",
      borderColor: alpha(theme.accent, 0.35),
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: theme.text, fontSize: 12 },
      extraCssText: "box-shadow:0 8px 26px rgba(0,0,0,.45);border-radius:2px;"
    };
  };

  var axisCommon = function () {
    return {
      axisLine: { lineStyle: { color: alpha(theme.dim, 0.28) } },
      axisTick: { show: false },
      axisLabel: { color: theme.dim, fontSize: 11 },
      splitLine: { lineStyle: { color: alpha(theme.dim, 0.12), type: "dashed" } }
    };
  };

  /* ---------------- trend：柱 + 线 复合 ---------------- */
  function buildTrend(el, d) {
    var x = (d && d.categories) || [];
    var series = (d && d.series) || [];
    var colors = [theme.accent, theme.warm, theme.accent2];

    var option = {
      color: colors,
      grid: { top: 34, left: 6, right: 14, bottom: 4, containLabel: true },
      tooltip: Object.assign(baseTooltip(), { trigger: "axis", axisPointer: { type: "shadow", shadowStyle: { color: alpha(theme.accent, 0.06) } } }),
      legend: { right: 4, top: 0, itemWidth: 8, itemHeight: 8, icon: "roundRect", textStyle: { color: theme.dim, fontSize: 11 } },
      xAxis: Object.assign({ type: "category", data: x, boundaryGap: true }, axisCommon()),
      yAxis: Object.assign({ type: "value", splitNumber: 4 }, axisCommon()),
      series: series.map(function (s, i) {
        if (s.type === "line") {
          return {
            name: s.name, type: "line", data: s.data, smooth: 0.35, symbol: "circle", symbolSize: 5, showSymbol: false,
            lineStyle: { width: 2, color: colors[i % colors.length], shadowBlur: 10, shadowColor: alpha(colors[i % colors.length], 0.5) },
            itemStyle: { color: colors[i % colors.length] },
            areaStyle: { color: vGrad(alpha(colors[i % colors.length], 0.28), alpha(colors[i % colors.length], 0)) },
            animationDuration: 900
          };
        }
        return {
          name: s.name, type: "bar", data: s.data, barWidth: 10, barGap: "30%",
          itemStyle: {
            color: vGrad(alpha(colors[i % colors.length], 0.95), alpha(colors[i % colors.length], 0.18)),
            borderRadius: [1, 1, 0, 0]
          },
          animationDelay: function (idx) { return idx * 30; }
        };
      })
    };
    make(el, option);
  }

  /* ---------------- types：玫瑰环图 ---------------- */
  function buildTypes(el, d) {
    var items = (d && d.items) || [];
    var total = items.reduce(function (a, b) { return a + Number(b.value || 0); }, 0);
    var palette = [theme.accent, theme.accent2, theme.warm, theme.ok, theme.warn, theme.danger, "#8b7cff"];

    var option = {
      color: palette,
      tooltip: Object.assign(baseTooltip(), { trigger: "item", formatter: "{b}<br/>{c} 件 · {d}%" }),
      legend: {
        orient: "vertical", right: 0, top: "middle", itemWidth: 7, itemHeight: 7, icon: "circle",
        itemGap: 10, textStyle: { color: theme.dim, fontSize: 11 },
        formatter: function (name) {
          var it = items.filter(function (x) { return x.name === name; })[0];
          return name + "  " + (it ? it.value : "");
        }
      },
      title: {
        text: "共 " + total.toLocaleString("zh-CN") + " 件",
        left: 4, top: 0,
        textStyle: { color: theme.faint, fontSize: 10, fontWeight: "normal" }
      },
      series: [{
        type: "pie", radius: ["50%", "70%"], center: ["30%", "52%"], roseType: "radius",
        avoidLabelOverlap: true, padAngle: 2,
        itemStyle: { borderColor: "rgba(3,10,22,.9)", borderWidth: 2, borderRadius: 2 },
        label: { show: false }, labelLine: { show: false },
        emphasis: { scale: true, scaleSize: 6, itemStyle: { shadowBlur: 18, shadowColor: alpha(theme.accent, 0.4) } },
        data: items
      }]
    };
    make(el, option);
  }

  /* ---------------- rank：横向条形 ---------------- */
  function buildRank(el, d) {
    var items = (d && d.items) || [];
    items = items.slice().sort(function (a, b) { return a.value - b.value; });
    var max = Math.max.apply(null, items.map(function (x) { return x.value; }).concat([1]));

    var option = {
      grid: { top: 4, left: 6, right: 44, bottom: 2, containLabel: true },
      tooltip: Object.assign(baseTooltip(), { trigger: "axis", axisPointer: { type: "shadow" } }),
      xAxis: { type: "value", max: max * 1.15, show: false },
      yAxis: {
        type: "category",
        data: items.map(function (x) { return x.name; }),
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: theme.dim, fontSize: 12, margin: 10 }
      },
      series: [{
        type: "bar", data: items.map(function (x, i) {
          var c = i === items.length - 1 ? theme.warm : theme.accent;
          return {
            value: x.value,
            itemStyle: { color: vGrad(alpha(c, 0.35), c), borderRadius: [0, 2, 2, 0] }
          };
        }),
        barWidth: 9, showBackground: true,
        backgroundStyle: { color: alpha(theme.dim, 0.10), borderRadius: 2 },
        label: { show: true, position: "right", color: theme.text, fontSize: 12, fontFamily: "Rajdhani, sans-serif" },
        animationDelay: function (i) { return i * 60; }
      }]
    };
    make(el, option);
  }

  /* ---------------- map：中国地图 + 涟漪 + 飞线 ---------------- */
  function buildMap(el, d) {
    var points = (d && d.points) || [];
    var lines = (d && d.lines) || [];
    if (!echarts.getMap("china")) {
      el.classList.add("is-empty");
      return;
    }
    el.classList.remove("is-empty");

    var byLevel = { normal: [], major: [], critical: [] };
    points.forEach(function (p) { (byLevel[p.level] || byLevel.normal).push(p); });

    var levelColor = { normal: theme.accent, major: theme.warm, critical: theme.danger };

    var provinces = (d && d.provinces) || [];
    var maxP = Math.max.apply(null, provinces.map(function (p) { return p.value; }).concat([1]));
    var provColors = ["#0b2d55", "#124a86", "#1a6cba", "#2490e0"];

    var series = [{
      type: "map", map: "china", roam: false, zoom: 1.32, center: [104, 35],
      data: provinces.map(function (p) {
        var idx = Math.min(3, Math.floor((p.value / maxP) * 4));
        return { name: p.name, value: p.value, itemStyle: { areaColor: provColors[idx] } };
      }),
      itemStyle: {
        areaColor: vGrad("#0b2b56", "#08203c"),
        borderColor: alpha(theme.accent, 0.42),
        borderWidth: 0.8,
        shadowColor: alpha(theme.accent, 0.28),
        shadowBlur: 18
      },
      emphasis: {
        label: { color: "#fff", fontSize: 11 },
        itemStyle: { areaColor: alpha(theme.accent, 0.28), borderColor: theme.accent }
      },
      label: { show: true, color: alpha(theme.dim, 0.85), fontSize: 9 },
      select: { disabled: true },
      z: 1
    }];

    if (lines.length) {
      series.push({
        type: "lines", coordinateSystem: "geo", zlevel: 2,
        effect: { show: true, period: 4, trailLength: 0.6, symbol: "arrow", symbolSize: 5, color: theme.warm },
        lineStyle: { color: alpha(theme.warm, 0.35), width: 1, curveness: 0.25, opacity: 0.7 },
        data: lines
      });
    }

    ["normal", "major", "critical"].forEach(function (lv, i) {
      var arr = byLevel[lv];
      if (!arr.length) return;
      series.push({
        type: "effectScatter", coordinateSystem: "geo", zlevel: 3,
        rippleEffect: { brushType: "stroke", scale: lv === "critical" ? 4.4 : 3.2, period: 3 },
        symbolSize: function (v) { return Math.max(6, Math.min(22, Math.sqrt(v[2] || 1) * 2.2)); },
        itemStyle: { color: levelColor[lv], shadowBlur: 12, shadowColor: levelColor[lv] },
        label: {
          show: lv !== "normal", position: "right", formatter: "{b}",
          color: theme.text, fontSize: 10
        },
        data: arr,
        z: 3 + i
      });
    });

    var option = {
      geo: {
        map: "china", roam: false, zoom: 1.32, center: [104, 35],
        itemStyle: { areaColor: "transparent", borderColor: "transparent" },
        silent: true, z: 0
      },
      tooltip: Object.assign(baseTooltip(), {
        trigger: "item",
        formatter: function (p) {
          if (p.seriesType === "effectScatter") return p.name + "<br/>事件 " + (p.value[2] || 0) + " 件";
          return p.name || "";
        }
      }),
      series: series
    };
    make(el, option);
  }

  /* ---------------- gauge：处置效率 ---------------- */
  function buildGauge(el, d) {
    var value = Number((d && d.value) || 0);
    var option = {
      series: [{
        type: "gauge", startAngle: 214, endAngle: -34, min: 0, max: 100, radius: "92%", center: ["50%", "58%"],
        progress: { show: true, width: 9, roundCap: true, itemStyle: { color: vGrad(theme.accent, theme.accent2) } },
        axisLine: { roundCap: true, lineStyle: { width: 9, color: [[1, alpha(theme.dim, 0.16)]] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: { offsetCenter: [0, "34%"], color: theme.dim, fontSize: 11 },
        detail: {
          offsetCenter: [0, "-2%"], valueAnimation: true,
          formatter: function (v) { return v.toFixed(0) + "%"; },
          color: theme.text, fontSize: 34, fontFamily: "Rajdhani, sans-serif", fontWeight: 600
        },
        data: [{ value: value, name: (d && d.label) || "按时办结率" }]
      }]
    };
    make(el, option);
  }

  /* ---------------- resource：双系列条形 ---------------- */
  function buildResource(el, d) {
    var items = (d && d.items) || [];
    var option = {
      grid: { top: 30, left: 6, right: 16, bottom: 2, containLabel: true },
      tooltip: Object.assign(baseTooltip(), { trigger: "axis", axisPointer: { type: "shadow" } }),
      legend: { right: 0, top: 0, itemWidth: 8, itemHeight: 8, icon: "roundRect", textStyle: { color: theme.dim, fontSize: 11 } },
      xAxis: Object.assign({ type: "value", splitNumber: 3 }, axisCommon()),
      yAxis: Object.assign({ type: "category", data: items.map(function (x) { return x.name; }) }, axisCommon(), {
        axisLine: { show: false }, splitLine: { show: false }, axisLabel: { color: theme.dim, fontSize: 11 }
      }),
      series: [
        {
          name: "已调度", type: "bar", stack: "r", barWidth: 11,
          itemStyle: { color: vGrad(alpha(theme.accent, 0.45), theme.accent), borderRadius: [2, 0, 0, 2] },
          data: items.map(function (x) { return x.done; })
        },
        {
          name: "待命", type: "bar", stack: "r", barWidth: 11,
          itemStyle: { color: alpha(theme.dim, 0.22), borderRadius: [0, 2, 2, 0] },
          data: items.map(function (x) { return x.idle; })
        }
      ]
    };
    make(el, option);
  }

  /* ---------------- radar：满意度 ---------------- */
  function buildRadar(el, d) {
    var ind = (d && d.indicators) || [];
    var series = (d && d.series) || [];
    var option = {
      color: [theme.accent, theme.warm],
      tooltip: Object.assign(baseTooltip(), { trigger: "item" }),
      legend: { right: 0, top: 0, itemWidth: 8, itemHeight: 8, icon: "roundRect", textStyle: { color: theme.dim, fontSize: 11 } },
      radar: {
        center: ["50%", "56%"], radius: "66%",
        indicator: ind.map(function (x) { return { name: x.name, max: x.max || 100 }; }),
        axisName: { color: theme.dim, fontSize: 10.5 },
        splitLine: { lineStyle: { color: alpha(theme.dim, 0.16) } },
        splitArea: { areaStyle: { color: [alpha(theme.accent, 0.03), "transparent"] } },
        axisLine: { lineStyle: { color: alpha(theme.dim, 0.16) } }
      },
      series: [{
        type: "radar", symbolSize: 4,
        data: series.map(function (s, i) {
          return {
            name: s.name, value: s.value,
            lineStyle: { width: 1.6, color: i ? theme.warm : theme.accent },
            itemStyle: { color: i ? theme.warm : theme.accent },
            areaStyle: { color: alpha(i ? theme.warm : theme.accent, 0.18) }
          };
        })
      }]
    };
    make(el, option);
  }

  /* ---------------- 基础设施 ---------------- */
  function make(el, option) {
    if (!el || !echarts) return null;
    var inst = echarts.getInstanceByDom(el) || echarts.init(el, null, { renderer: "canvas" });
    charts[el.id] = inst;
    inst.setOption(option, { notMerge: true });
    return inst;
  }

  var REGISTRY = {
    trend: buildTrend,
    types: buildTypes,
    rank: buildRank,
    map: buildMap,
    gauge: buildGauge,
    resource: buildResource,
    radar: buildRadar
  };

  /* 每类图表在 snapshot 里的取值路径 */
  var DATA_PATH = {
    trend: "series.trend",
    types: "series.types",
    rank: "series.rank",
    map: "geo",
    gauge: "series.gauge",
    resource: "series.resource",
    radar: "series.radar"
  };

  function resolve(name, viewData) {
    var path = DATA_PATH[name];
    if (!path) return null;
    var v = viewData && path.indexOf("series.") === 0 ? viewData[path.slice(7)] : null;
    return v || global.DashboardData.get(path);
  }

  function renderOne(el) {
    var name = el.getAttribute("data-chart");
    var builder = REGISTRY[name];
    if (!builder) return;
    var d = resolve(name, currentViewData);
    if (!d) { el.classList.add("is-empty"); return; }
    el.classList.remove("is-empty");
    builder(el, d);
  }

  var currentViewData = null;

  function renderAll() {
    theme = readTheme();
    Array.prototype.forEach.call(document.querySelectorAll("[data-chart]"), renderOne);
  }

  function setView(view) {
    currentView = view;
    currentViewData = global.DashboardData.get("views." + view, null);
    renderAll();
    // 视图切换时给面板一个轻微入场动画
    Array.prototype.forEach.call(document.querySelectorAll(".panel"), function (p) {
      p.classList.remove("view-enter");
      void p.offsetWidth;
      p.classList.add("view-enter");
    });
  }

  var resizeTimer = null;
  function resizeAll() {
    Object.keys(charts).forEach(function (k) {
      try { charts[k].resize(); } catch (e) {}
    });
  }

  function observe() {
    var els = document.querySelectorAll("[data-chart]");
    Array.prototype.forEach.call(els, function (el) {
      if (typeof ResizeObserver !== "undefined") {
        var ro = new ResizeObserver(function () { resizeAll(); });
        ro.observe(el);
        observers.push(ro);
      }
    });
    global.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resizeAll, 120);
    });
  }

  /* 首次渲染前加载中国地图；失败不影响其他图表 */
  function ensureMap() {
    if (echarts.getMap("china")) return Promise.resolve();
    return fetch("./data/china.json").then(function (r) {
      if (!r.ok) throw new Error("map geojson " + r.status);
      return r.json();
    }).then(function (geo) {
      echarts.registerMap("china", geo);
    }).catch(function (e) {
      console.warn("[charts] 地图资源加载失败，跳过地图：", e.message);
    });
  }

  function init() {
    ensureMap().then(function () {
      theme = readTheme();
      renderAll();
      observe();
    });
    global.DashboardData.on("data", function () { renderAll(); });
  }

  global.DashboardCharts = {
    init: init,
    renderAll: renderAll,
    resizeAll: resizeAll,
    setView: setView,
    get view() { return currentView; }
  };
})(window);
