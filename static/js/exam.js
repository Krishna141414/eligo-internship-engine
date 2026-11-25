/* Exam page behaviour: autosave each answer, mark answered questions in the palette, and confirm
   submission with the unanswered count. Contains no answer data (hard rule 8). */
(function () {
  "use strict";
  var form = document.getElementById("exam-form");
  if (!form) return;
  var saveUrl = form.dataset.saveUrl;
  var csrf = form.querySelector("input[name=csrfmiddlewaretoken]").value;

  form.addEventListener("change", function (e) {
    var input = e.target;
    if (input.type !== "radio") return;
    var qid = input.name.slice(2);
    var body = new URLSearchParams({ question: qid, option: input.value });
    fetch(saveUrl, { method: "POST", headers: { "X-CSRFToken": csrf }, body: body, credentials: "same-origin" })
      .catch(function () { /* the full form is still posted on submit */ });
    var chip = document.querySelector('#palette [data-qid="' + qid + '"]');
    if (chip) { chip.classList.remove("btn-outline-secondary"); chip.classList.add("btn-secondary"); }
  });

  form.addEventListener("submit", function (e) {
    if (form.dataset.confirmed === "1") return;
    var total = form.querySelectorAll(".exam-question").length;
    var answered = new Set(Array.from(form.querySelectorAll("input[type=radio]:checked")).map(function (i) { return i.name; })).size;
    var left = total - answered;
    if (left > 0 && e.isTrusted && !window.confirm("You have " + left + " unanswered question" + (left === 1 ? "" : "s") + ". Submit anyway?")) {
      e.preventDefault();
      return;
    }
    form.dataset.confirmed = "1";
  });
})();
