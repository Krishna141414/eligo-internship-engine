/* Exam countdown. DISPLAY ONLY: the server enforces the deadline (hard rule 9).
   Shows "m:ss left", counts down from the server-provided remaining seconds, changes colour and icon at
   5 minutes and 1 minute, announces those marks to screen readers, and submits the form at 0. */
(function () {
  "use strict";
  var box = document.getElementById("timer");
  var out = document.getElementById("timer-value");
  var announce = document.getElementById("timer-announce");
  var form = document.getElementById("exam-form");
  var icon = document.getElementById("timer-icon");
  var ICONS = { normal: "bi-clock", warning: "bi-hourglass-split", critical: "bi-exclamation-triangle" };
  if (!box || !out || !form) return;
  var end = Date.now() + parseInt(box.dataset.remaining || "0", 10) * 1000;
  var submitted = false;
  var lastState = null;

  function fmt(s) {
    var m = Math.floor(s / 60), r = s % 60;
    return m + ":" + (r < 10 ? "0" : "") + r;
  }
  function tick() {
    var left = Math.max(0, Math.round((end - Date.now()) / 1000));
    var state = left <= 60 ? "critical" : left <= 300 ? "warning" : "normal";
    out.textContent = fmt(left) + " left";
    box.dataset.state = state;
    // Not colour alone: the icon changes with the state (and screen readers get the announcements below).
    if (icon) icon.className = "bi " + ICONS[state];
    if (announce && lastState !== null && state !== lastState) {
      announce.textContent = state === "critical" ? "Less than 1 minute left." : "Less than 5 minutes left.";
    }
    lastState = state;
    if (left === 0 && !submitted) {
      submitted = true;
      out.textContent = "0:00 left, submitting";
      form.dataset.confirmed = "1";
      form.submit();
      return;
    }
    window.setTimeout(tick, 1000);
  }
  tick();
})();
