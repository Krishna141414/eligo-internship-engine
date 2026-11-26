/* Shell behaviour: Bootstrap form styling for Django widgets, the admin sidebar toggle,
   and the busy state on long-running forms. Everything works without this file. */
(function () {
  "use strict";
  // Django renders plain widgets; give them Bootstrap classes once, here, instead of in every form.
  document.querySelectorAll("form input, form select, form textarea").forEach(function (el) {
    if (el.type === "hidden" || el.closest(".tag-input")) return;
    if (el.type === "checkbox" || el.type === "radio") { if (!el.closest(".option")) el.classList.add("form-check-input"); return; }
    el.classList.add(el.tagName === "SELECT" ? "form-select" : "form-control");
    var help = document.getElementById(el.id + "_help");
    if (help) el.setAttribute("aria-describedby", help.id);
  });
  document.querySelectorAll("form ul[id] > li > label > input[type=checkbox]").forEach(function (input) {
    var li = input.closest("li");
    li.classList.add("form-check");
    input.parentNode.classList.add("form-check-label");
  });

  // Bootstrap tooltips (e.g. what the match % means). The same text is in each button's aria-label.
  if (window.bootstrap) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) { new window.bootstrap.Tooltip(el); });
  }

  var toggle = document.querySelector("[data-sidebar-toggle]");
  var sidebar = document.getElementById("app-sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      var open = sidebar.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("is-open")) {
        sidebar.classList.remove("is-open"); toggle.setAttribute("aria-expanded", "false"); toggle.focus();
      }
    });
  }

  // After a failed submit, focus the first invalid field (Django marks it aria-invalid="true").
  var firstInvalid = document.querySelector('form [aria-invalid="true"]');
  if (firstInvalid) firstInvalid.focus();

  // Destructive actions ask first.
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.dataset.confirm)) e.preventDefault();
    });
  });

  // Long forms warn before leaving with unsaved changes.
  document.querySelectorAll("form[data-warn-unsaved]").forEach(function (form) {
    var dirty = false;
    form.addEventListener("input", function () { dirty = true; });
    form.addEventListener("change", function () { dirty = true; });
    form.addEventListener("submit", function () { dirty = false; });
    window.addEventListener("beforeunload", function (e) {
      if (dirty) { e.preventDefault(); e.returnValue = ""; }
    });
  });

  // Forms marked data-busy show their status message and disable the button while the server works.
  document.querySelectorAll("form[data-busy]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var box = document.getElementById(form.dataset.busy);
      if (box) { box.classList.add("is-on"); box.setAttribute("aria-hidden", "false"); }
      form.querySelectorAll("button[type=submit]").forEach(function (b) { b.disabled = true; b.setAttribute("aria-busy", "true"); });
    });
  });
})();
