const form = document.getElementById("authPageForm");
const status = document.getElementById("authPageStatus");
form.addEventListener("submit", async event => {
  event.preventDefault();
  const page = form.dataset.page;
  const button = event.submitter;
  status.textContent = "";
  if (!FieldErrors.validate(form)) return;
  const payload = {};
  payload.username = document.getElementById("usernameInput").value;
  payload.password = document.getElementById("passwordInput").value;
  if (page === "register" && payload.password !== document.getElementById("registerConfirmPassword").value) {
    FieldErrors.set(document.getElementById("registerConfirmPassword"), "Hai m\u1eadt kh\u1ea9u ch\u01b0a tr\u00f9ng nhau.");
    document.getElementById("registerConfirmPassword").focus();
    return;
  }
  button.disabled = true;
  try {
    await api(`/api/auth/${page}`, {method: "POST", body: JSON.stringify(payload)});
    location.assign("/");
  } catch (error) {
    if (error.status === 401) error.message = "T\u00ean \u0111\u0103ng nh\u1eadp ho\u1eb7c m\u1eadt kh\u1ea9u kh\u00f4ng \u0111\u00fang.";
    if (error.status === 409) error.message = "T\u00ean \u0111\u0103ng nh\u1eadp \u0111\u00e3 t\u1ed3n t\u1ea1i.";
    FieldErrors.report(error, {username:document.getElementById("usernameInput"), password:document.getElementById("passwordInput")}, document.getElementById(error.status===409?"usernameInput":"passwordInput"));
  }
  finally { button.disabled = false; }
});

document.querySelectorAll("[data-password-target]").forEach(button => {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.passwordTarget);
    const visible = input.type === "password";
    input.type = visible ? "text" : "password";
    button.setAttribute("aria-pressed", String(visible));
    button.setAttribute("aria-label", visible ? "\u1ea8n m\u1eadt kh\u1ea9u" : "Hi\u1ec7n m\u1eadt kh\u1ea9u");
  });
});
