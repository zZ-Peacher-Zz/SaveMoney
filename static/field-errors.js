window.FieldErrors = (() => {
  function slot(input) {
    const id=input.id+"Error";
    let node=document.getElementById(id);
    if(!node){
      node=document.createElement("span");node.id=id;node.className="field-error";node.setAttribute("aria-live","polite");
      const password=input.closest(".password-field");
      if(password)password.append(node);
      else if(input.parentElement.classList.contains("input-row")) {
        const wrapper=document.createElement("div");wrapper.className="field-control";input.before(wrapper);wrapper.append(input,node);
      } else input.after(node);
      input.setAttribute("aria-describedby",[input.getAttribute("aria-describedby"),id].filter(Boolean).join(" "));
    }
    return node;
  }
  function clear(input){if(!input)return;const node=document.getElementById(input.id+"Error");if(node)node.textContent="";input.removeAttribute("aria-invalid");}
  function set(input,message){if(!input)return;slot(input).textContent=message;input.setAttribute("aria-invalid","true");}
  function validation(input){
    const v=input.validity;
    if(v.valueMissing)return "Vui l\u00f2ng nh\u1eadp th\u00f4ng tin n\u00e0y.";
    if(v.tooShort)return `C\u1ea7n \u00edt nh\u1ea5t ${input.minLength} k\u00fd t\u1ef1.`;
    if(v.tooLong)return `T\u1ed1i \u0111a ${input.maxLength} k\u00fd t\u1ef1.`;
    if(v.patternMismatch)return "Ch\u1ec9 d\u00f9ng ch\u1eef, s\u1ed1, d\u1ea5u ch\u1ea5m, g\u1ea1ch ngang ho\u1eb7c g\u1ea1ch d\u01b0\u1edbi.";
    if(v.rangeUnderflow)return `Gi\u00e1 tr\u1ecb ph\u1ea3i t\u1eeb ${input.min} tr\u1edf l\u00ean.`;
    if(v.rangeOverflow)return `Gi\u00e1 tr\u1ecb kh\u00f4ng \u0111\u01b0\u1ee3c v\u01b0\u1ee3t ${input.max}.`;
    if(v.stepMismatch)return `Gi\u00e1 tr\u1ecb ph\u1ea3i theo b\u01b0\u1edbc ${input.step}.`;
    return "Vui l\u00f2ng nh\u1eadp gi\u00e1 tr\u1ecb h\u1ee3p l\u1ec7.";
  }
  function validate(target){
    const inputs=target.matches("input,select,textarea")?[target]:[...target.querySelectorAll("input,select,textarea")];
    let first;
    for(const input of inputs){clear(input);if(input.willValidate&&!input.validity.valid){set(input,validation(input));first ||= input;}}
    if(first)first.focus();return !first;
  }
  function reset(form){form.querySelectorAll("input,select,textarea").forEach(clear);}
  function report(error,fields,fallback){
    let first;
    if(Array.isArray(error.details))for(const detail of error.details){
      const key=detail.loc?.[detail.loc.length-1], input=fields[key];
      if(input){set(input,detail.msg.replace(/^Value error, /,""));first ||= input;}
    }
    if(!first&&fallback){set(fallback,error.message);first=fallback;}
    first?.focus();
  }
  document.querySelectorAll("form").forEach(form=>{form.noValidate=true;form.addEventListener("reset",()=>reset(form));});
  for(const event of ["input","change"])document.addEventListener(event,e=>{if(e.target.matches("input,select,textarea"))clear(e.target);});
  return {set,clear,validate,reset,report};
})();
