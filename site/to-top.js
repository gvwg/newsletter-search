// Back-to-top button, shared by index.html and search.html. Shown once the
// reader has scrolled more than one screen down.
const button = document.createElement("a");
button.className = "to-top";
button.href = "#";
button.hidden = true;
button.innerHTML = '<span aria-hidden="true">&uarr;</span> Top';
button.setAttribute("aria-label", "Back to top");
button.addEventListener("click", (e) => {
  e.preventDefault();
  const smooth = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  scrollTo({ top: 0, behavior: smooth ? "smooth" : "auto" });
  document.querySelector("main").focus({ preventScroll: true });
});
document.body.append(button);
const update = () => { button.hidden = scrollY < innerHeight; };
addEventListener("scroll", update, { passive: true });
update();
