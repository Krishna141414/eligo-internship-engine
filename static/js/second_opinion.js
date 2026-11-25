/* AI second opinion (D-025): after the deterministic ranking has rendered, ask the local LLM to
   cross-check each pending card, one at a time so a small local model is not flooded. The page
   never waits for this; without scripting the cards simply keep their rule-based check. */
(function () {
  "use strict";
  var boxes = Array.prototype.slice.call(document.querySelectorAll("[data-second-opinion-url][data-state='pending']"));
  if (!boxes.length) return;
  var tokenInput = document.querySelector("input[name=csrfmiddlewaretoken]");
  var csrf = tokenInput ? tokenInput.value : "";

  function render(box, data) {
    var out = box.querySelector("[data-second-opinion-text]");
    box.dataset.state = data.status;
    if (data.status === "done") {
      out.textContent = data.missing.length
        ? "AI second opinion: the local model also flags " + data.missing.join(", ") + "."
        : "AI second opinion: the local model found no extra missing skills.";
    } else {
      out.textContent = "AI second opinion not available right now. The rule-based check above stands.";
    }
  }

  function next() {
    var box = boxes.shift();
    if (!box) return;
    fetch(box.dataset.secondOpinionUrl, {
      method: "POST", credentials: "same-origin",
      headers: { "X-CSRFToken": csrf, "Accept": "application/json" }
    })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) { render(box, data); })
      .catch(function () { render(box, { status: "unavailable", missing: [] }); })
      .then(next);
  }
  next();
})();
