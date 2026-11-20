(function () {
  // Typesets the equations that the Markdown build marks with the "arithmatex" class, using KaTeX (loaded before this script).
  var BS = String.fromCharCode(92);
  function render() {
    if (typeof renderMathInElement !== "function") return;
    Array.prototype.forEach.call(document.querySelectorAll(".arithmatex"), function (node) {
      renderMathInElement(node, {
        delimiters: [
          { left: BS + "[", right: BS + "]", display: true },
          { left: BS + "(", right: BS + ")", display: false },
        ],
        throwOnError: false,
      });
    });
  }
  if (typeof document$ !== "undefined" && document$.subscribe) document$.subscribe(render);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render);
  else render();
})();
