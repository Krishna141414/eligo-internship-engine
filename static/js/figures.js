/* ML page: open a notebook figure full size in a dialog. Without scripting the link opens the image. */
(function () {
  "use strict";
  var modalEl = document.getElementById("figure-modal");
  if (!modalEl || !window.bootstrap) return;
  var modal = new window.bootstrap.Modal(modalEl);
  var img = modalEl.querySelector("img");
  var title = modalEl.querySelector(".modal-title");
  document.querySelectorAll("a[data-enlarge]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      img.src = a.href;
      img.alt = "Notebook figure: " + a.dataset.caption;
      title.textContent = a.dataset.caption;
      modal.show();
    });
  });
})();
