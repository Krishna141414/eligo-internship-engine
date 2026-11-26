/* Profile form enhancements. Both work on top of plain inputs, so the form posts the same data
   without scripting: the skills box stays a comma-separated text field, career skills stay checkboxes. */
(function () {
  "use strict";

  // Career-skill picker: selected skills show as removable chips at the top; the list below is only
  // for adding (selected rows are hidden from it). Filter + live count. Without JS: plain checkboxes.
  document.querySelectorAll("[data-skill-picker]").forEach(function (picker) {
    var filter = picker.querySelector("[data-skill-filter]");
    var count = picker.querySelector("[data-skill-count]");
    var chips = picker.querySelector("[data-skill-chips]");
    var items = Array.prototype.slice.call(picker.querySelectorAll(".skill-picker__list .form-check"));

    function render() {
      var selected = items.filter(function (it) { return it.querySelector("input").checked; });
      items.forEach(function (it) { it.classList.toggle("is-selected", it.querySelector("input").checked); });
      count.textContent = selected.length;
      if (!chips) return;
      chips.innerHTML = "";
      if (!selected.length) {
        var none = document.createElement("li");
        none.className = "skill-picker__empty";
        none.textContent = "None selected yet. Add skills from the list below.";
        chips.appendChild(none);
      }
      selected.forEach(function (it) {
        var input = it.querySelector("input");
        var name = it.querySelector("label").textContent.trim();
        var li = document.createElement("li");
        li.className = "chip chip--matched";
        li.appendChild(document.createTextNode(name));
        var x = document.createElement("button");
        x.type = "button";
        x.setAttribute("aria-label", "Remove " + name);
        x.innerHTML = '<i class="bi bi-x" aria-hidden="true"></i>';
        x.addEventListener("click", function () {
          input.checked = false;
          render();
          (filter || chips).focus();
        });
        li.appendChild(x);
        chips.appendChild(li);
      });
    }
    picker.addEventListener("change", render);
    if (filter) {
      filter.addEventListener("input", function () {
        var q = filter.value.trim().toLowerCase();
        items.forEach(function (it) {
          it.classList.toggle("is-filtered", q !== "" && it.textContent.toLowerCase().indexOf(q) === -1);
        });
      });
      filter.addEventListener("keydown", function (e) { if (e.key === "Enter") e.preventDefault(); });
    }
    render();
  });

  // Free-text skills as removable chips. The original input becomes hidden and holds "a, b, c".
  document.querySelectorAll("input[data-tag-input]").forEach(function (source) {
    var tags = source.value.split(",").map(function (s) { return s.trim(); }).filter(Boolean);
    var box = document.createElement("div");
    box.className = "tag-input";
    var list = document.createElement("ul");
    list.className = "chips";
    list.setAttribute("aria-label", "Added skills");
    var entry = document.createElement("input");
    entry.type = "text";
    entry.autocomplete = "off";
    entry.setAttribute("list", source.dataset.tagInput);
    entry.id = source.id;
    source.id = source.id + "_value";
    if (source.getAttribute("aria-describedby")) entry.setAttribute("aria-describedby", source.getAttribute("aria-describedby"));
    if (source.getAttribute("aria-invalid")) entry.setAttribute("aria-invalid", source.getAttribute("aria-invalid"));
    source.type = "hidden";
    source.parentNode.insertBefore(box, source);
    box.appendChild(list);
    box.appendChild(entry);

    function sync() { source.value = tags.join(", "); }
    function render() {
      list.innerHTML = "";
      tags.forEach(function (t, i) {
        var li = document.createElement("li");
        li.className = "chip chip--neutral";
        li.appendChild(document.createTextNode(t));
        var x = document.createElement("button");
        x.type = "button";
        x.setAttribute("aria-label", "Remove " + t);
        x.innerHTML = '<i class="bi bi-x" aria-hidden="true"></i>';
        x.addEventListener("click", function () { tags.splice(i, 1); render(); sync(); entry.focus(); });
        li.appendChild(x);
        list.appendChild(li);
      });
    }
    function add(raw) {
      raw.split(",").map(function (s) { return s.trim(); }).filter(Boolean).forEach(function (t) {
        if (tags.map(function (s) { return s.toLowerCase(); }).indexOf(t.toLowerCase()) === -1) tags.push(t);
      });
      entry.value = "";
      render(); sync();
    }
    entry.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(entry.value); }
      else if (e.key === "Backspace" && entry.value === "" && tags.length) { tags.pop(); render(); sync(); }
    });
    entry.addEventListener("change", function () { if (entry.value.trim()) add(entry.value); });
    entry.form.addEventListener("submit", function () { if (entry.value.trim()) add(entry.value); });
    render();
  });
})();
