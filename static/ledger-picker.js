(() => {
  const select = document.getElementById("ledgerPicker");
  const wrap = select.closest(".ledger-select-wrap");
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "ledger-trigger";
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-labelledby", "ledgerPickerLabel ledgerSelectedLabel");
  const label = document.createElement("span");
  label.id = "ledgerSelectedLabel";
  trigger.append(label);
  const menu = document.createElement("div");
  menu.id = "ledgerOptions";
  menu.className = "ledger-options";
  menu.setAttribute("role", "listbox");
  menu.setAttribute("aria-labelledby", "ledgerPickerLabel");
  menu.hidden = true;
  trigger.setAttribute("aria-controls", menu.id);
  select.before(trigger);
  wrap.append(menu);
  select.hidden = true;
  let active = 0;
  function close(focus = false) {
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    if (focus) trigger.focus({preventScroll: true});
  }
  function render() {
    label.textContent = select.selectedOptions[0]?.textContent || "Cá nhân";
    menu.replaceChildren(...[...select.options].map((option, index) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "ledger-option";
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", String(option.selected));
      item.tabIndex = -1;
      const icon = document.createElement("span");
      icon.className = "ledger-option-icon";
      icon.textContent = option.value ? "⌂" : "♙";
      icon.setAttribute("aria-hidden", "true");
      const text = document.createElement("span");
      text.textContent = option.textContent;
      const check = document.createElement("span");
      check.className = "ledger-option-check";
      check.textContent = option.selected ? "✓" : "";
      check.setAttribute("aria-hidden", "true");
      item.append(icon, text, check);
      item.addEventListener("click", () => {
        select.value = option.value;
        close(true);
        render();
        select.dispatchEvent(new Event("change", {bubbles: true}));
      });
      item.addEventListener("focus", () => { active = index; });
      return item;
    }));
  }
  function focusOption(index) {
    active = (index + menu.children.length) % menu.children.length;
    menu.children[active]?.focus({preventScroll: true});
    menu.children[active]?.scrollIntoView({block: "nearest"});
  }
  function open() {
    render();
    menu.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    focusOption(Math.max(select.selectedIndex, 0));
  }
  trigger.addEventListener("click", () => menu.hidden ? open() : close());
  trigger.addEventListener("keydown", event => {
    if (["ArrowDown", "ArrowUp"].includes(event.key)) { event.preventDefault(); open(); }
  });
  menu.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); close(true); }
    else if (event.key === "Tab") close();
    else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      focusOption(event.key === "Home" ? 0 : event.key === "End" ? menu.children.length - 1 : active + (event.key === "ArrowDown" ? 1 : -1));
    }
  });
  document.addEventListener("pointerdown", event => { if (!wrap.contains(event.target)) close(); });
  wrap.addEventListener("focusout", event => { if (!wrap.contains(event.relatedTarget)) close(); });
  select.addEventListener("change", render);
  document.addEventListener("family-ledger-changed", render);
  new MutationObserver(render).observe(select, {childList: true, subtree: true});
  render();
})();
