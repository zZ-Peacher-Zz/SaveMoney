const form = document.getElementById("authPageForm");
const status = document.getElementById("authPageStatus");
form.addEventListener("submit", async event => {
  event.preventDefault();
  const page = form.dataset.page;
  const button = event.submitter;
  status.textContent = "";
  const payload = {};
  payload.username = document.getElementById("usernameInput").value;
  payload.password = document.getElementById("passwordInput").value;
  if (page === "register" && payload.password !== document.getElementById("registerConfirmPassword").value) {
    status.textContent = "Hai mật khẩu chưa trùng nhau.";
    return;
  }
  button.disabled = true;
  try {
    await api(`/api/auth/${page}`, {method: "POST", body: JSON.stringify(payload)});
    location.assign("/");
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
});
