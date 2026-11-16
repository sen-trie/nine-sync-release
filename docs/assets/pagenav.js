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
