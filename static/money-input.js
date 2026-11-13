window.MoneyInput = (() => {
  const formatter = new Intl.NumberFormat("vi-VN", {maximumFractionDigits:0});
  function digits(value) { return String(value).replace(/[.,\s]/g, ""); }
  function parse(input) { return input.value === "" ? 0 : Number(digits(input.value)); }
  function check(input) {
    const raw = digits(input.value);
    let error = "";
    if (raw && !/^\d+$/.test(raw)) error = "Ch\u1ec9 nh\u1eadp s\u1ed1 ti\u1ec1n nguy\u00ean, kh\u00f4ng \u00e2m.";
    else if (raw && !Number.isSafeInteger(Number(raw))) error = "S\u1ed1 ti\u1ec1n qu\u00e1 l\u1edbn. Vui l\u00f2ng nh\u1eadp l\u1ea1i.";
    else if (raw && Number(raw) < Number(input.dataset.minAmount || 0)) error = "S\u1ed1 ti\u1ec1n ph\u1ea3i l\u1edbn h\u01a1n 0.";
    input.setCustomValidity(error);
    return !error;
  }
  function format(value) { return value === "" || value == null ? "" : formatter.format(Number(value)); }
  function set(input,value) {input.value=format(value);check(input);}
  document.querySelectorAll("[data-money-input]").forEach(input => {
    input.addEventListener("input", () => {
      if (input.isComposing) return;
      if (!check(input)) return;
      const before = digits(input.value.slice(0,input.selectionStart)).length;
      const raw = digits(input.value);
      if (!raw) {input.value="";return;}
      input.value = format(raw);
      let count=0,caret=0;
      while(caret<input.value.length && count<before) {if(/\d/.test(input.value[caret])) count++;caret++;}
      input.setSelectionRange(caret,caret);
    });
    input.form?.addEventListener("reset",()=>input.setCustomValidity(""));
  });
  return {parse,set,format};
})();
