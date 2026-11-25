/* Exam countdown. DISPLAY ONLY: the server enforces the deadline (hard rule 9).
   Counts down from the server-provided remaining seconds and submits the form at 0. */
(function () {
  "use strict";
  var box = document.getElementById("timer");
  var out = document.getElementById("timer-value");
  var form = document.getElementById("exam-form");
  if (!box || !out || !form) return;
  var end = Date.now() + parseInt(box.dataset.remaining || "0", 10) * 1000;
  var submitted = false;

  function fmt(s) {
    var m = Math.floor(s / 60), r = s % 60;
    return m + ":" + (r < 10 ? "0" : "") + r;
  }
  function tick() {
    var left = Math.max(0, Math.round((end - Date.now()) / 1000));
    var label = left <= 60 ? " (under 1 minute)" : left <= 300 ? " (under 5 minutes)" : "";
    out.textContent = fmt(left) + label;
    box.dataset.state = left <= 60 ? "critical" : left <= 300 ? "warning" : "normal";
    if (left === 0 && !submitted) {
      submitted = true;
      out.textContent = "0:00 (time is up, submitting)";
      form.submit();
      return;
    }
    window.setTimeout(tick, 1000);
  }
  tick();
})();
