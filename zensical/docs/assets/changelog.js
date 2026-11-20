(function () {
  var FILTERS = [["all", "All"], ["core", "Core"], ["fx", "FX"], ["bundle", "Bundled"]];

  function setup() {
    var holder = document.getElementById("cl-filter");
    if (!holder || holder.dataset.ready) return;
    holder.dataset.ready = "1";
    var article = holder.closest("article") || holder.parentNode;
    var buttons = [];

    function apply(kind) {
      var current = "all";
      Array.prototype.forEach.call(article.children, function (node) {
        if (node.classList.contains("cl-h")) current = node.getAttribute("data-comp") || "all";
        else if (node.id === "cl-filter" || !seenFirstHeading(node)) return;
        node.classList.toggle("cl-hidden", kind !== "all" && current !== kind);
      });
      buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.kind === kind)); });
      try { history.replaceState(null, "", kind === "all" ? location.pathname : "#" + kind); } catch (e) {}
    }

    function seenFirstHeading(node) {
      var first = article.querySelector(".cl-h");
      return !!first && (first === node || !!(first.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING));
    }

    FILTERS.forEach(function (f) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = f[1];
      b.dataset.kind = f[0];
      b.addEventListener("click", function () { apply(f[0]); });
      buttons.push(b);
      holder.appendChild(b);
    });
    var wanted = (location.hash || "").replace("#", "");
    apply(FILTERS.some(function (f) { return f[0] === wanted; }) ? wanted : "all");
  }

  if (typeof document$ !== "undefined" && document$.subscribe) document$.subscribe(setup);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
  else setup();
})();
