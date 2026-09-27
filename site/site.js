// Shared by index.html and search.html.

// "Back" goes back to where the reader came from, like the browser's Back
// button, so returning to the list keeps its open years and scroll position.
// Arriving directly (bookmark, typed address, new tab) leaves the page's own
// fallback link in place (gvwg.ca home, or the issue list).
const back = document.querySelector("a.back");
if (back && document.referrer && history.length > 1) {
  let from = null;
  try { from = new URL(document.referrer); } catch { /* unreadable referrer: keep fallback */ }
  if (from && (from.hostname === "gvwg.ca" || from.hostname === "www.gvwg.ca"
               || from.origin === location.origin)) {
    back.textContent = from.origin === location.origin ? "\u2039 Back" : "\u2039 Back to gvwg.ca";
    back.addEventListener("click", (e) => { e.preventDefault(); history.back(); });
  }
}

// Back-to-top button, shown once the reader has scrolled more than a screen.
const toTop = document.createElement("a");
toTop.className = "to-top";
toTop.href = "#";
toTop.hidden = true;
toTop.innerHTML = '<span aria-hidden="true">&uarr;</span> Top';
toTop.setAttribute("aria-label", "Back to top");
toTop.addEventListener("click", (e) => {
  e.preventDefault();
  const smooth = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  scrollTo({ top: 0, behavior: smooth ? "smooth" : "auto" });
  document.querySelector("main").focus({ preventScroll: true });
});
document.body.append(toTop);
const update = () => { toTop.hidden = scrollY < innerHeight; };
addEventListener("scroll", update, { passive: true });
update();
