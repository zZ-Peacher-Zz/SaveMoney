import * as React from "react";
import { createRoot } from "react-dom/client";
import { vi } from "date-fns/locale";
import { Calendar } from "./calendar";
import { Button } from "./button";

const incomeButton = document.getElementById("openIncomeDialog");
if (incomeButton) {
  const mount = document.createElement("span");
  mount.className = "income-button-mount";
  incomeButton.replaceWith(mount);
  createRoot(mount).render(
    <Button id="openIncomeDialog" type="button" variant="default"
      className="shadcn-income-button min-h-11 rounded-xl px-3 text-base"
      aria-label="Thêm thu nhập" aria-haspopup="dialog" aria-controls="incomeDialog">
      <span className="income-action-full">Thêm thu nhập</span>
      <span className="income-action-short">Thêm thu</span>
    </Button>
  );
}

function parse(value) {
  if (!/^\d{4}-\d{2}(-\d{2})?$/.test(value)) return undefined;
  const [y, m, d = 1] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}
function iso(date, monthOnly) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}${monthOnly ? "" : `-${String(date.getDate()).padStart(2, "0")}`}`;
}
function DatePicker({input, wrapper, monthOnly}) {
  const [open, setOpen] = React.useState(false);
  const [selected, setSelected] = React.useState();
  const [month, setMonth] = React.useState(new Date());
  const [bounds, setBounds] = React.useState({});
  const popup = React.useRef();
  React.useEffect(() => {
    const show = () => {
      const date = parse(input.value);
      setSelected(date);
      setMonth(date || parse(input.min) || new Date());
      setBounds({min: parse(input.min), max: parse(input.max)});
      setOpen(true);
    };
    const keyboard = e => {
      if (["ArrowDown", "Enter", " "].includes(e.key)) { e.preventDefault(); show(); }
    };
    const outside = e => { if (!wrapper.contains(e.target)) setOpen(false); };
    const close = () => setOpen(false);
    const form = input.form;
    const dialog = input.closest("dialog");
    input.addEventListener("click", show);
    input.addEventListener("keydown", keyboard);
    document.addEventListener("pointerdown", outside);
    form?.addEventListener("reset", close);
    dialog?.addEventListener("close", close);
    return () => {
      input.removeEventListener("click", show);
      input.removeEventListener("keydown", keyboard);
      document.removeEventListener("pointerdown", outside);
      form?.removeEventListener("reset", close);
      dialog?.removeEventListener("close", close);
    };
  }, []);
  React.useLayoutEffect(() => {
    input.setAttribute("aria-expanded", String(open));
    if (open && popup.current) {
      popup.current.style.left = "0px";
      const rect = popup.current.getBoundingClientRect();
      if (rect.right > innerWidth - 12) popup.current.style.left = `${innerWidth - 12 - rect.right}px`;
    }
  }, [open]);
  if (!open) return null;
  return <div ref={popup} id={`${input.id}Calendar`} className="shadcn-date-popover" role="dialog" aria-label={monthOnly ? "Chọn tháng" : "Chọn ngày"}
    onKeyDown={e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setOpen(false); input.focus(); } }}>
    <Calendar mode="single" locale={vi} selected={selected} month={month} onMonthChange={setMonth}
      formatters={{formatMonthDropdown: date => date.toLocaleDateString("vi-VN", {month: "short"})}}
      captionLayout="dropdown" startMonth={new Date(1970, 0)} endMonth={new Date(2100, 11)}
      disabled={[...(bounds.min ? [{before: bounds.min}] : []), ...(bounds.max ? [{after: bounds.max}] : [])]}
      autoFocus onSelect={date => {
        if (!date) return;
        input.value = iso(date, monthOnly);
        setSelected(date); setOpen(false);
        input.dispatchEvent(new Event("input", {bubbles: true}));
        input.dispatchEvent(new Event("change", {bubbles: true}));
        input.focus({preventScroll: true});
      }} />
    <button type="button" className="shadcn-calendar-close" onClick={() => {setOpen(false);input.focus();}}>Đóng lịch</button>
  </div>;
}
for (const id of ["monthPicker", "dateInput", "historyFrom", "historyTo"]) {
  const input = document.getElementById(id);
  if (!input) continue;
  const value = input.value;
  input.type = "text";
  input.value = value;
  input.readOnly = true;
  input.setAttribute("aria-haspopup", "dialog");
  input.setAttribute("aria-controls", `${id}Calendar`);
  input.setAttribute("aria-expanded", "false");
  input.classList.add("shadcn-date-input");
  const wrapper = document.createElement("span");
  wrapper.className = "shadcn-date-field";
  input.before(wrapper);wrapper.append(input);
  const mount = document.createElement("span");wrapper.append(mount);
  createRoot(mount).render(<DatePicker input={input} wrapper={wrapper} monthOnly={id === "monthPicker"} />);
}
