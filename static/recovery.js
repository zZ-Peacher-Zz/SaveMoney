async function refreshRecoveryEmail() {
  const version = accountVersion;
  try {
    const profile = await api("/api/auth/recovery-email");
    if (version !== accountVersion) return;
    document.getElementById("recoveryEmailStatus").textContent = profile.email
      ? `Email đã xác minh: ${profile.email}`
      : "Chưa có email khôi phục đã xác minh. Thêm email và mở link trong thư để bảo vệ tài khoản.";
  } catch (error) { showToast(error.message); }
}
document.addEventListener("account-ready", () => {
  document.getElementById("recoveryEmailForm").reset();
  document.getElementById("recoveryEmailMessage").textContent = "";
  refreshRecoveryEmail();
});

document.getElementById("recoveryEmailForm").addEventListener("submit", async event => {
  event.preventDefault();
  const button = event.submitter;
  const status = document.getElementById("recoveryEmailMessage");
  button.disabled = true;
  try {
    await api("/api/auth/recovery-email", {method: "PUT", body: JSON.stringify({
      email: document.getElementById("recoveryEmailInput").value.trim(),
      password: document.getElementById("recoveryPasswordInput").value
    })});
    document.getElementById("recoveryPasswordInput").value = "";
    status.textContent = "Đã gửi email xác minh. Mở link trong thư và bấm Xác minh email. Link có hiệu lực 30 phút.";
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
});
