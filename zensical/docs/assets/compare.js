/* Before/after comparison slider.
 *
 * Markup (inside any page; Markdown allows raw HTML):
 *
 *   <figure class="ns-compare" data-label-a="Original MMD" data-label-b="Initial Blender Import" data-ratio="16/9">
 *     <img src="../../assets/images/gallery/effect-mmd.webp" alt="...">
 *     <img src="../../assets/images/gallery/effect-import.webp" alt="...">
 *     <figcaption>Optional caption</figcaption>
 *   </figure>
 *
 * The first image (A) is shown on the left of the divider, the second (B) on the right. With fewer than two images the
 * missing side is drawn as a labelled placeholder, so pages can be laid out before the renders exist. Dragging, touch,
 * and the arrow keys (Shift for larger steps, Home/End for the extremes) move the divider. The expand button opens the
 * same comparison larger in the site lightbox without interfering with the divider.
 */
(function () {
  "use strict";

  var EXPAND_SVG =
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M5 5h5v2H7v3H5zm9 0h5v5h-2V7h-3zM5 14h2v3h3v2H5zm12 0h2v5h-5v-2h3z"/></svg>';

  function side(cls, label, src, alt) {
    var pane = document.createElement("div");
    pane.className = "ns-compare-pane ns-compare-" + cls;
    if (src) {
      var img = document.createElement("img");
      img.src = src;
      img.alt = alt || label;
      img.draggable = false;
      img.decoding = "async";
      pane.appendChild(img);
    } else {
      var ph = document.createElement("div");
      ph.className = "ns-compare-placeholder";
      ph.innerHTML = "<strong></strong><span>Image to be added</span>";
      ph.firstChild.textContent = label;
      pane.appendChild(ph);
    }
    return pane;
  }

  function label(cls, text) {
    var tag = document.createElement("span");
    tag.className = "ns-compare-label ns-compare-label-" + cls;
    tag.textContent = text;
    return tag;
  }

  function frame(cfg, large) {
    var box = document.createElement("div");
    box.className = "ns-compare-frame" + (large ? " ns-compare-large" : "");
    box.style.setProperty("--ns-ratio", cfg.ratio);
    var a = side("a", cfg.labelA, cfg.srcA, cfg.altA);
    var b = side("b", cfg.labelB, cfg.srcB, cfg.altB);
    var handle = document.createElement("div");
    handle.className = "ns-compare-handle";
    handle.tabIndex = 0;
    handle.setAttribute("role", "slider");
    handle.setAttribute("aria-label", "Comparison divider: " + cfg.labelA + " on the left, " + cfg.labelB + " on the right");
    handle.setAttribute("aria-valuemin", "0");
    handle.setAttribute("aria-valuemax", "100");
    handle.innerHTML = '<span class="ns-compare-knob" aria-hidden="true"></span>';
    box.appendChild(b);
    box.appendChild(a);
    box.appendChild(label("a", cfg.labelA));
    box.appendChild(label("b", cfg.labelB));
    box.appendChild(handle);

    var position = cfg.position;
    function set(value) {
      position = Math.min(100, Math.max(0, value));
      cfg.position = position;
      box.style.setProperty("--ns-pos", position + "%");
      a.style.clipPath = "inset(0 " + (100 - position) + "% 0 0)";
      handle.setAttribute("aria-valuenow", String(Math.round(position)));
      handle.setAttribute("aria-valuetext", Math.round(position) + "% " + cfg.labelA);
    }
    set(position);

    function fromEvent(event) {
      var r = box.getBoundingClientRect();
      set(((event.clientX - r.left) / r.width) * 100);
    }
    var dragging = false;
    box.addEventListener("pointerdown", function (event) {
      if (event.target.closest(".ns-compare-expand")) return;
      if (event.pointerType === "mouse" && event.button !== 0) return;
      dragging = true;
      box.setPointerCapture(event.pointerId);
      box.classList.add("ns-compare-dragging");
      fromEvent(event);
    });
    box.addEventListener("pointermove", function (event) {
      if (dragging) fromEvent(event);
    });
    function stop(event) {
      dragging = false;
      box.classList.remove("ns-compare-dragging");
      if (box.hasPointerCapture && box.hasPointerCapture(event.pointerId)) box.releasePointerCapture(event.pointerId);
    }
    box.addEventListener("pointerup", stop);
    box.addEventListener("pointercancel", stop);
    handle.addEventListener("keydown", function (event) {
      var step = event.shiftKey ? 10 : 2;
      if (event.key === "ArrowLeft" || event.key === "ArrowDown") set(position - step);
      else if (event.key === "ArrowRight" || event.key === "ArrowUp") set(position + step);
      else if (event.key === "Home") set(0);
      else if (event.key === "End") set(100);
      else return;
      event.preventDefault();
    });

    if (!large && window.NineSyncLightbox) {
      var expand = document.createElement("button");
      expand.type = "button";
      expand.className = "ns-compare-expand";
      expand.setAttribute("aria-label", "Open comparison larger");
      expand.title = "Open larger";
      expand.innerHTML = EXPAND_SVG;
      expand.addEventListener("click", function (event) {
        event.stopPropagation();
        var wrap = document.createElement("div");
        wrap.className = "ns-compare ns-compare-expanded";
        wrap.appendChild(frame(cfg, true));
        window.NineSyncLightbox.openNode(wrap, cfg.title);
      });
      box.appendChild(expand);
    }
    return box;
  }

  function init(root) {
    if (root.dataset.nsReady) return;
    root.dataset.nsReady = "1";
    var images = Array.prototype.slice.call(root.querySelectorAll("img"));
    var caption = root.querySelector("figcaption");
    var cfg = {
      labelA: root.dataset.labelA || "Before",
      labelB: root.dataset.labelB || "After",
      srcA: images[0] ? images[0].getAttribute("src") : "",
      srcB: images[1] ? images[1].getAttribute("src") : "",
      altA: images[0] ? images[0].alt : "",
      altB: images[1] ? images[1].alt : "",
      ratio: root.dataset.ratio || "16 / 9",
      position: parseFloat(root.dataset.position || "50"),
      title: caption ? caption.textContent.trim() : root.dataset.labelA + " / " + root.dataset.labelB,
    };
    images.forEach(function (img) { img.remove(); });
    root.insertBefore(frame(cfg, false), root.firstChild);
  }

  function scan() {
    Array.prototype.forEach.call(document.querySelectorAll(".ns-compare"), function (node) {
      if (!node.closest(".ns-lb")) init(node);
    });
  }

  if (typeof document$ !== "undefined" && document$.subscribe) document$.subscribe(scan);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", scan);
  else scan();
})();
