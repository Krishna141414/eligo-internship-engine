/* Eligo charts (Chart.js 4, vendored). Colours and fonts are read from the theme tokens in
   css/theme.css so the palette lives in one place. Data always comes from a json_script block the
   server rendered from real values; this file never computes or invents a number. No animation. */
(function () {
  "use strict";
  if (!window.Chart) return;
  var css = getComputedStyle(document.documentElement);
  function token(name) { return css.getPropertyValue(name).trim(); }
  var C = {
    navy: token("--navy-900"), navy600: token("--navy-600"), navy100: token("--navy-100"),
    amber: token("--amber"), success: token("--success"), danger: token("--danger"),
    muted: token("--muted"), text: token("--text"), border: token("--border")
  };
  window.EligoPalette = C;

  Chart.defaults.font.family = token("--font-body") || "Inter, system-ui, sans-serif";
  Chart.defaults.font.size = 13;
  Chart.defaults.color = C.muted;
  Chart.defaults.animation = false;
  Chart.defaults.plugins.legend.display = false;
  Chart.defaults.maintainAspectRatio = false;

  function data(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  /* Long axis labels are shortened with an ellipsis; the tooltip and the "Show the numbers" table keep the full text. */
  function shorten(label, max) {
    label = String(label);
    return label.length > max ? label.slice(0, max - 1).trimEnd() + "…" : label;
  }

  /* Horizontal bars: one series, first bar highlighted. `suffix` formats ticks and tooltips. */
  function hbar(canvasId, d, opts) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || !d || !d.labels || !d.labels.length) return null;
    opts = opts || {};
    var colours = d.labels.map(function (_, i) { return i === 0 && opts.highlightFirst ? C.navy : (opts.colour || C.navy600); });
    return new Chart(canvas, {
      type: "bar",
      data: { labels: d.labels, datasets: [{ data: d.values, backgroundColor: colours, borderRadius: 4, barThickness: 18 }] },
      options: {
        indexAxis: "y",
        scales: {
          x: { beginAtZero: true, max: opts.max, grid: { color: C.border }, border: { display: false },
               ticks: { precision: opts.integer ? 0 : undefined, callback: function (v) { return v + (opts.suffix || ""); } } },
          y: { grid: { display: false }, border: { display: false },
               ticks: { color: C.text, callback: function (v) {
                 // About a third of the chart width for labels: ~26 characters on desktop, ~14 on a phone.
                 var max = Math.max(10, Math.min(opts.labelMax || 26, Math.floor(this.chart.width / 22)));
                 return shorten(this.getLabelForValue(v), max); } } }
        },
        plugins: { tooltip: { callbacks: {
          title: function (items) { return items[0].label; },
          label: function (ctx) { return " " + ctx.parsed.x + (opts.suffix || ""); } } } }
      }
    });
  }
  window.EligoCharts = { hbar: hbar, data: data };

  /* Two series per model (accuracy navy, macro F1 amber), in percent. */
  function modelComparison(canvasId, d) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || !d || !d.labels || !d.labels.length) return null;
    return new Chart(canvas, {
      type: "bar",
      data: { labels: d.labels, datasets: [
        { label: "Accuracy", data: d.accuracy, backgroundColor: C.navy, borderRadius: 4, maxBarThickness: 40 },
        { label: "F1 (macro)", data: d.f1_macro, backgroundColor: C.amber, borderRadius: 4, maxBarThickness: 40 }] },
      options: {
        scales: {
          y: { beginAtZero: true, max: 100, grid: { color: C.border }, border: { display: false },
               ticks: { callback: function (v) { return v + "%"; } } },
          x: { grid: { display: false }, border: { display: false }, ticks: { color: C.text } }
        },
        plugins: { tooltip: { callbacks: { label: function (ctx) { return " " + ctx.dataset.label + ": " + ctx.parsed.y + "%"; } } } }
      }
    });
  }
  window.EligoCharts.modelComparison = modelComparison;

  hbar("role-chart", data("role-chart-data"), { max: 100, suffix: "%", highlightFirst: true });
  hbar("feature-chart", data("feature-chart-data"), { colour: C.navy600 });
  hbar("recs-chart", data("recs-chart-data"), { colour: C.navy, integer: true });
  modelComparison("ml-chart", data("ml-chart-data"));
})();
