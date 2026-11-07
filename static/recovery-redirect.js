// Redirect legacy emailed links before dashboard authentication starts.
const legacyRecovery = new URLSearchParams(location.hash.slice(1));
if (legacyRecovery.get("token") && ["reset", "verify"].includes(legacyRecovery.get("action"))) {
  const target = legacyRecovery.get("action") === "reset" ? "/reset-password" : "/verify-email";
  location.replace(target + location.hash);
}
