(() => {
  for (const [dialogId, openerId, closeId] of [
    ["familyManager", "openFamilyManager", "closeFamilyManager"],
    ["incomeDialog", "openIncomeDialog", "closeIncomeDialog"],
    ["historyFilterDialog", "openHistoryFilters", "closeHistoryFilters"],
    ["insightDialog", "openInsight", "closeInsight"]
  ]) {
    const dialog = document.getElementById(dialogId);
    let scrollY = 0;
    const saved = {};
    document.addEventListener("click", event => {
      if (!event.target.closest(`#${openerId}`)) return;
      if (dialog.open) return;
      scrollY = window.scrollY;
      for (const key of ["position", "top", "width", "overflow"]) saved[key] = document.body.style[key];
      document.body.style.position = "fixed";
      document.body.style.top = `-${scrollY}px`;
      document.body.style.width = "100%";
      document.body.style.overflow = "hidden";
      dialog.showModal();
    });
    document.getElementById(closeId).addEventListener("click", () => dialog.close());
    const outside = event => {
      const rect = dialog.getBoundingClientRect();
      return event.clientX < rect.left || event.clientX > rect.right ||
        event.clientY < rect.top || event.clientY > rect.bottom;
    };
    let startedOutside = false;
    dialog.addEventListener("pointerdown", event => {
      startedOutside = event.target === dialog && outside(event);
    });
    dialog.addEventListener("click", event => {
      if (startedOutside && event.target === dialog && outside(event)) dialog.close();
      startedOutside = false;
    });
    dialog.addEventListener("close", () => {
      for (const key of Object.keys(saved)) document.body.style[key] = saved[key];
      window.scrollTo(0, scrollY);
      document.getElementById(openerId)?.focus({preventScroll: true});
    });
  }
})();

window.confirmDelete = message => {
  const dialog = document.getElementById("deleteConfirmDialog");
  if (dialog.open) return Promise.resolve(false);
  const previousFocus = document.activeElement;
  const y = window.scrollY;
  const saved = {};
  for (const key of ["position", "top", "width", "overflow"]) saved[key] = document.body.style[key];
  Object.assign(document.body.style, {position: "fixed", top: `-${y}px`, width: "100%", overflow: "hidden"});
  dialog.returnValue = "cancel";
  document.getElementById("deleteConfirmMessage").textContent = message;
  return new Promise(resolve => {
    const cancel = () => dialog.close("cancel");
    const outside = event => {
      const rect = dialog.getBoundingClientRect();
      return event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom;
    };
    let startedOutside = false;
    const down = event => { startedOutside = event.target === dialog && outside(event); };
    const click = event => { if (startedOutside && event.target === dialog && outside(event)) cancel(); startedOutside = false; };
    const closeButton = document.getElementById("closeDeleteConfirm");
    closeButton.addEventListener("click", cancel);
    dialog.addEventListener("pointerdown", down);
    dialog.addEventListener("click", click);
    dialog.addEventListener("close", () => {
      closeButton.removeEventListener("click", cancel);
      dialog.removeEventListener("pointerdown", down);
      dialog.removeEventListener("click", click);
      Object.assign(document.body.style, saved);
      window.scrollTo(0, y);
      previousFocus?.focus({preventScroll: true});
      resolve(dialog.returnValue === "delete");
    }, {once: true});
    dialog.showModal();
  });
};
