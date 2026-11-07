const recoveryLink = new URLSearchParams(location.hash.slice(1));
const recoveryAction = location.pathname === "/verify-email" ? "verify" : "reset";
let recoveryToken = recoveryLink.get("token");
const recoveryDialog = document.getElementById("recoveryDialog");
if (recoveryToken && ["verify", "reset"].includes(recoveryAction)) {
  history.replaceState(null, "", location.pathname + location.search);
  const verify = recoveryAction === "verify";
  document.getElementById("recoveryTitle").textContent = verify ? "Xác minh email khôi phục" : "Đặt lại mật khẩu";
  document.getElementById("resetPasswordFields").classList.toggle("hidden", verify);
  document.getElementById("newPassword").required = !verify;
  document.getElementById("confirmPassword").required = !verify;
  document.getElementById("submitRecoveryLink").textContent = verify ? "Xác minh email" : "Lưu mật khẩu mới";

} else {
  document.getElementById("recoveryLinkStatus").textContent = "Link không có mã khôi phục. Mở lại link đầy đủ trong email hoặc yêu cầu link mới.";
  document.getElementById("submitRecoveryLink").disabled = true;
}
document.getElementById("recoveryLinkForm").addEventListener("submit", async event => {
  event.preventDefault();
  const status = document.getElementById("recoveryLinkStatus");
  const button = event.submitter;
  if (!recoveryToken) return;
  const password = document.getElementById("newPassword").value;
  if (recoveryAction === "reset" && password !== document.getElementById("confirmPassword").value) {
    status.textContent = "Hai mật khẩu chưa trùng nhau.";
    return;
  }
  button.disabled = true;
  try {
    await api(`/api/auth/${recoveryAction === "verify" ? "verify-email" : "reset-password"}`, {
      method: "POST", body: JSON.stringify({token: recoveryToken, ...(recoveryAction === "reset" ? {password} : {})})
    });
    recoveryToken = null;
    if (recoveryAction === "reset") {
      status.textContent = "Đã đổi mật khẩu. Bạn có thể đăng nhập bằng mật khẩu mới.";
    } else {
      status.textContent = "Email đã được xác minh. Bạn có thể dùng email này để khôi phục mật khẩu.";
    }
    document.getElementById("newPassword").value = "";
    document.getElementById("confirmPassword").value = "";
    button.classList.add("hidden");
  } catch (error) { status.textContent = error.message; button.disabled = false; }
});
