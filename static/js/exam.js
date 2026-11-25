/* Exam page behaviour: one question per view with a palette, autosave of each answer, and a confirm
   step that shows the unanswered count. Contains no answer data (hard rule 8). Without scripting every
   question is on the page and the form posts normally. */
(function () {
  "use strict";
  var form = document.getElementById("exam-form");
  if (!form) return;
  var saveUrl = form.dataset.saveUrl;
  var csrf = form.querySelector("input[name=csrfmiddlewaretoken]").value;
  var questions = Array.prototype.slice.call(form.querySelectorAll(".question"));
  var buttons = Array.prototype.slice.call(document.querySelectorAll("#palette .palette__btn"));
  var prev = form.querySelector("[data-exam-prev]");
  var next = form.querySelector("[data-exam-next]");
  var countOut = document.getElementById("answered-count");
  var current = 0;

  function isAnswered(q) { return !!q.querySelector("input[type=radio]:checked"); }
  function answeredCount() { return questions.filter(isAnswered).length; }

  function show(i, focus) {
    current = Math.max(0, Math.min(questions.length - 1, i));
    questions.forEach(function (q, k) { q.hidden = k !== current; });
    buttons.forEach(function (b, k) {
      if (k === current) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
    });
    if (prev) prev.disabled = current === 0;
    if (next) next.disabled = current === questions.length - 1;
    if (focus) {
      var legend = questions[current].querySelector("legend");
      legend.setAttribute("tabindex", "-1");
      legend.focus();
    }
  }

  buttons.forEach(function (b, k) {
    b.addEventListener("click", function (e) { e.preventDefault(); show(k, true); });
  });
  if (prev) prev.addEventListener("click", function () { show(current - 1, true); });
  if (next) next.addEventListener("click", function () { show(current + 1, true); });

  form.addEventListener("change", function (e) {
    var input = e.target;
    if (input.type !== "radio") return;
    var qid = input.name.slice(2);
    var body = new URLSearchParams({ question: qid, option: input.value });
    fetch(saveUrl, { method: "POST", headers: { "X-CSRFToken": csrf }, body: body, credentials: "same-origin" })
      .catch(function () { /* the full form is still posted on submit */ });
    var chip = document.querySelector('#palette [data-qid="' + qid + '"]');
    if (chip) {
      chip.dataset.answered = "true";
      chip.setAttribute("aria-label", "Question " + chip.textContent.trim() + ", answered");
    }
    if (countOut) countOut.textContent = answeredCount();
  });

  var modalEl = document.getElementById("confirm-submit");
  var modal = modalEl && window.bootstrap ? new window.bootstrap.Modal(modalEl) : null;
  var go = document.getElementById("confirm-submit-go");
  if (go) go.addEventListener("click", function () { form.dataset.confirmed = "1"; form.submit(); });

  form.addEventListener("submit", function (e) {
    if (form.dataset.confirmed === "1" || !e.isTrusted) return;
    var left = questions.length - answeredCount();
    var text = left > 0
      ? "You've answered " + (questions.length - left) + " of " + questions.length + " questions. " + left +
        " unanswered question" + (left === 1 ? "" : "s") + " will score 0."
      : "You've answered all " + questions.length + " questions.";
    e.preventDefault();
    if (modal) {
      document.getElementById("confirm-submit-text").textContent = text;
      modal.show();
    } else if (window.confirm(text + " Submit now?")) {
      form.dataset.confirmed = "1";
      form.submit();
    }
  });

  // Start on the first unanswered question.
  var firstOpen = questions.findIndex(function (q) { return !isAnswered(q); });
  show(firstOpen === -1 ? 0 : firstOpen, false);
})();
