const form = document.getElementById("authPageForm");
const status = document.getElementById("authPageStatus");
if (new URLSearchParams(location.search).get("reset") === "success") {
  status.textContent = "Đã đổi mật khẩu. Bạn hãy đăng nhập bằng mật khẩu mới.";
}
form.addEventListener("submit", async event => {
  event.preventDefault();
  const page = form.dataset.page;
  const button = event.submitter;
  status.textContent = "";
  const payload = {};
  if (page !== "forgot-password") {
    payload.username = document.getElementById("usernameInput").value;
    payload.password = document.getElementById("passwordInput").value;
  }
  if (page !== "login") payload.email = document.getElementById("emailInput").value.trim();
  if (page === "register" && payload.password !== document.getElementById("registerConfirmPassword").value) {
    status.textContent = "Hai mật khẩu chưa trùng nhau.";
    return;
  }
  button.disabled = true;
  try {
    await api(`/api/auth/${page}`, {method: "POST", body: JSON.stringify(payload)});
    if (page === "forgot-password") {
      status.textContent = "Nếu email đã được đăng ký và xác minh, bạn sẽ nhận được link đặt lại mật khẩu. Hãy kiểm tra cả thư rác.";
    } else {
      location.assign("/");
    }
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
});
