(() => {
  const dialog = document.getElementById("familyManager");
  const opener = document.getElementById("openFamilyManager");
  let scrollY = 0;
  const saved = {};
  opener.addEventListener("click", () => {
    if (dialog.open) return;
    scrollY = window.scrollY;
    for (const key of ["position", "top", "width", "overflow"]) saved[key] = document.body.style[key];
    document.body.style.position = "fixed";
    document.body.style.top = `-${scrollY}px`;
    document.body.style.width = "100%";
    document.body.style.overflow = "hidden";
    dialog.showModal();
  });
  document.getElementById("closeFamilyManager").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => {
    for (const key of Object.keys(saved)) document.body.style[key] = saved[key];
    window.scrollTo(0, scrollY);
    opener.focus({preventScroll: true});
  });
})();
