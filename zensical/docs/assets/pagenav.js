(function () {
  // Moves the theme's previous/next links (navigation.footer) from the full-width footer into the end of the page body.
  function move() {
    var inner = document.querySelector(".md-footer__inner");
    var article = document.querySelector("article.md-content__inner");
    if (!inner || !article || article.querySelector(".ns-pagenav")) return;
    var links = inner.querySelectorAll(".md-footer__link");
    if (!links.length) return;
    var nav = document.createElement("nav");
    nav.className = "ns-pagenav";
    nav.setAttribute("aria-label", "Previous and next page");
    Array.prototype.forEach.call(links, function (a) { nav.appendChild(a); });
    article.appendChild(nav);
    inner.hidden = true;
  }
  if (typeof document$ !== "undefined" && document$.subscribe) document$.subscribe(move);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", move);
  else move();
})();

(function () {
  // Marks the Examples pages so the stylesheet can drop their heading permalinks (see extra.css).
  function mark() {
    document.documentElement.classList.toggle("ns-examples", /\/examples\//.test(location.pathname));
  }
  if (typeof document$ !== "undefined" && document$.subscribe) document$.subscribe(mark);
  else mark();
})();

(function () {
  // Sidebar groups that the stylesheet starts closed (see extra.css) are given the theme's own closed state here, so that the
  // first click on their arrow opens them. The stylesheet hides them until this runs, so nothing shifts.
  function settle() {
    var toggles = document.querySelectorAll('.md-nav--primary input.md-toggle--indeterminate[id^="__nav_"]');
    Array.prototype.forEach.call(toggles, function (box) {
      if (box.checked) return;
      var path = box.id.replace("__nav_", "").split("_");
      var item = box.closest(".md-nav__item");
      var last = item && item === item.parentElement.lastElementChild;
      if (path.length < 3 && !(path.length === 2 && last)) return;
      box.classList.remove("md-toggle--indeterminate");
      box.indeterminate = false;
      box.checked = false;
    });
    var root = document.documentElement;
    if (!root.classList.contains("ns-nav-ready")) {
      void root.offsetHeight;
      requestAnimationFrame(function () { root.classList.add("ns-nav-ready"); });
    }
  }
  if (typeof document$ !== "undefined" && document$.subscribe) document$.subscribe(settle);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", settle);
  else settle();
})();
