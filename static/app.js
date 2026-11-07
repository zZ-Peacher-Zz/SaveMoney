const monthPicker = document.getElementById("monthPicker");
const incomeInput = document.getElementById("incomeInput");
const dateInput = document.getElementById("dateInput");
const categoryInput = document.getElementById("categoryInput");
const amountInput = document.getElementById("amountInput");
const noteInput = document.getElementById("noteInput");
const expenseForm = document.getElementById("expenseForm");
const expenseBody = document.getElementById("expenseBody");
const breakdown = document.getElementById("breakdown");
const emptyState = document.getElementById("emptyState");
const tableWrap = document.getElementById("tableWrap");
const cancelEditBtn = document.getElementById("cancelEditBtn");
const toast = document.getElementById("toast");

let editingId = null;
let familyGroups = [];
const ledgerPicker = document.getElementById("ledgerPicker");
let loadVersion = 0;

function ledgerUrl(url) {
  return ledgerPicker.value ? `${url}?group_id=${encodeURIComponent(ledgerPicker.value)}` : url;
}

function selectedGroup() {
  return familyGroups.find(group => String(group.id) === ledgerPicker.value);
}

const now = new Date();
const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
monthPicker.value = currentMonth;

function money(value) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0
  }).format(Number(value || 0));
}

function formatDate(value) {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function html(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add("hidden"), 2200);
}

async function api(url, options = {}) {
  if (url.startsWith("/api/months/") || url.startsWith("/api/expenses")) url = ledgerUrl(url);
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    let message = "Có lỗi xảy ra";
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch (_) {}
    if (response.status === 401) showAuth();
    if (Array.isArray(message)) message = message.map(item => item.msg).join("; ");
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

function defaultDate() {
  if (monthPicker.value === currentMonth) {
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, "0");
    const dd = String(now.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }
  return `${monthPicker.value}-01`;
}

function resetForm() {
  editingId = null;
  expenseForm.reset();
  categoryInput.value = "Ăn uống";
  dateInput.value = defaultDate();
  document.getElementById("formTitle").textContent = "Thêm khoản chi";
  document.getElementById("submitBtn").textContent = "Thêm khoản chi";
  cancelEditBtn.classList.add("hidden");
}

async function loadAll() {
  const requestVersion = ++loadVersion;
  const version = accountVersion;
  const month = monthPicker.value;
  const [summary, expenses] = await Promise.all([
    api(`/api/months/${month}/summary`),
    api(`/api/months/${month}/expenses`)
  ]);

  if (version !== accountVersion || requestVersion !== loadVersion) return;
  renderSummary(summary);
  renderBreakdown(summary);
  renderExpenses(expenses);

  incomeInput.value = summary.my_income || "";
  document.getElementById("exportBtn").href = ledgerUrl(`/api/months/${month}/export.csv`);
}

function renderSummary(summary) {
  document.getElementById("incomeValue").textContent = money(summary.income);
  document.getElementById("expenseValue").textContent = money(summary.total_expense);
  document.getElementById("expenseCount").textContent = `${summary.expense_count} khoản chi`;

  const remaining = document.getElementById("remainingValue");
  remaining.textContent = money(summary.remaining);
  remaining.className = summary.remaining >= 0 ? "positive" : "negative";

  document.getElementById("savingRate").textContent = `${summary.saving_rate.toFixed(1)}%`;

  document.getElementById("budgetAlert").classList.toggle(
    "hidden",
    !(summary.income > 0 && summary.total_expense > summary.income)
  );
}

function renderBreakdown(summary) {
  if (!summary.categories.length) {
    breakdown.innerHTML = `<div class="breakdown-empty">Chưa có dữ liệu để phân tích.</div>`;
    return;
  }

  const total = summary.total_expense || 1;

  breakdown.innerHTML = summary.categories.map(item => {
    const pct = item.amount / total * 100;
    return `
      <div class="bar-row">
        <div class="bar-label" title="${html(item.category)}">${html(item.category)}</div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${pct}%"></div>
        </div>
        <div class="bar-value">${money(item.amount)}</div>
      </div>
    `;
  }).join("");
}

function renderExpenses(items) {
  document.getElementById("tableHint").textContent = `${items.length} giao dịch`;
  emptyState.classList.toggle("hidden", items.length > 0);
  tableWrap.classList.toggle("hidden", items.length === 0);

  const days = new Map();
  for (const item of items) {
    if (!days.has(item.expense_date)) days.set(item.expense_date, []);
    days.get(item.expense_date).push(item);
  }

  expenseBody.innerHTML = [...days.keys()].sort().reverse().map(day => {
    const expenses = days.get(day);
    const total = expenses.reduce((sum, item) => sum + Number(item.amount), 0);
    return `
    <tr class="day-heading">
      <th colspan="5">
        <div class="day-summary">
          <span>${formatDate(day)} <small>· ${expenses.length} khoản chi</small></span>
          <span>Tổng ngày: ${money(total)}</span>
        </div>
      </th>
    </tr>
    ${expenses.map(item => `
    <tr>
      <td>${formatDate(item.expense_date)}</td>
      <td><span class="tag">${html(item.category)}</span>${ledgerPicker.value ? `<small class="record-author">${html(item.username)}</small>` : ""}</td>
      <td>${html(item.note || "—")}</td>
      <td class="amount">${money(item.amount)}</td>
      <td>
        <div class="row-actions">
          ${item.can_edit ? `<button class="icon-button" data-action="edit" data-id="${item.id}">Sửa</button>
          <button class="icon-button" data-action="delete" data-id="${item.id}">Xoá</button>` : ""}
        </div>
      </td>
    </tr>
    `).join("")}`;
  }).join("");

  expenseBody.querySelectorAll("[data-action='edit']").forEach(button => {
    button.addEventListener("click", () => editExpense(Number(button.dataset.id), items));
  });

  expenseBody.querySelectorAll("[data-action='delete']").forEach(button => {
    button.addEventListener("click", () => deleteExpense(Number(button.dataset.id)));
  });
}

async function editExpense(id, items) {
  const item = items.find(x => x.id === id);
  if (!item) return;

  editingId = id;
  dateInput.value = item.expense_date;
  categoryInput.value = item.category;
  amountInput.value = item.amount;
  noteInput.value = item.note || "";

  document.getElementById("formTitle").textContent = "Sửa khoản chi";
  document.getElementById("submitBtn").textContent = "Lưu thay đổi";
  cancelEditBtn.classList.remove("hidden");

  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function deleteExpense(id) {
  if (!confirm("Xoá khoản chi này?")) return;

  try {
    await api(`/api/expenses/${id}`, { method: "DELETE" });
    await loadAll();
    showToast("Đã xoá khoản chi");
  } catch (error) {
    showToast(error.message);
  }
}

document.getElementById("saveIncomeBtn").addEventListener("click", async () => {
  try {
    await api(`/api/months/${monthPicker.value}/income`, {
      method: "PUT",
      body: JSON.stringify({
        amount: Number(incomeInput.value || 0)
      })
    });

    await loadAll();
    showToast("Đã cập nhật thu nhập");
  } catch (error) {
    showToast(error.message);
  }
});

expenseForm.addEventListener("submit", async event => {
  event.preventDefault();

  if (!dateInput.value.startsWith(monthPicker.value)) {
    showToast("Ngày chi tiêu phải thuộc tháng đang chọn");
    return;
  }

  const payload = {
    expense_date: dateInput.value,
    category: categoryInput.value,
    amount: Number(amountInput.value),
    note: noteInput.value.trim() || null
  };

  try {
    if (editingId) {
      await api(`/api/expenses/${editingId}`, {
        method: "PUT",
        body: JSON.stringify(payload)
      });
      showToast("Đã cập nhật khoản chi");
    } else {
      await api("/api/expenses", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      showToast("Đã thêm khoản chi");
    }

    resetForm();
    await loadAll();
  } catch (error) {
    showToast(error.message);
  }
});

cancelEditBtn.addEventListener("click", resetForm);

monthPicker.addEventListener("change", async () => {
  resetForm();
  try { await loadAll(); } catch (error) { showToast(error.message); }
});

document.getElementById("clearBtn").addEventListener("click", async () => {
  if (!confirm("Xoá toàn bộ dữ liệu của tháng này?")) return;

  try {
    await api(`/api/months/${monthPicker.value}`, {
      method: "DELETE"
    });

    resetForm();
    await loadAll();
    showToast("Đã xoá dữ liệu tháng");
  } catch (error) {
    showToast(error.message);
  }
});

const dashboard = document.getElementById("dashboard");
let accountVersion = 0;
let invitationTimer = null;
let invitationPolling = false;
let invitationBusy = false;
let invitationRevision = 0;
let invitationSnapshot = "";

function showAuth() {
  accountVersion++;
  clearInterval(invitationTimer);
  location.replace("/login" + location.hash);
}

async function showDashboard(user) {
  document.getElementById("currentUser").textContent = user.username;
  document.getElementById("avatarInitial").textContent = user.username.slice(0, 1).toUpperCase();
  const profile = await api("/api/auth/me");
  renderAvatar(profile.avatar_url);
  resetForm();
  await refreshGroups();
  await loadAll();
  dashboard.classList.remove("hidden");
  clearInterval(invitationTimer);
  invitationTimer = setInterval(pollInvitations, 3000);
  document.dispatchEvent(new Event("account-ready"));
}

function renderAvatar(url) {
  const image = document.getElementById("avatarImage");
  image.classList.toggle("hidden", !url);
  document.getElementById("avatarInitial").classList.toggle("hidden", !!url);
  document.getElementById("removeAvatarBtn").classList.toggle("hidden", !url);
  if (url) image.src = `${url}?v=${Date.now()}`;
  else image.removeAttribute("src");
}

document.getElementById("avatarBtn").addEventListener("click", () => document.getElementById("avatarInput").click());
document.getElementById("avatarInput").addEventListener("change", async event => {
  const file = event.target.files[0];
  if (!file) return;
  const version = accountVersion;
  const button = document.getElementById("avatarBtn");
  button.disabled = true;
  event.target.disabled = true;
  try {
    if (file.size > 5 * 1024 * 1024) throw new Error("Ảnh không được lớn hơn 5 MB");
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) throw new Error("Chọn ảnh PNG, JPG hoặc WebP");
    const cropped = await openAvatarCrop(file);
    if (!cropped || version !== accountVersion) return;
    const result = await api("/api/auth/avatar", {method: "PUT", headers: {"Content-Type": "image/png"}, body: cropped});
    if (version !== accountVersion) return;
    renderAvatar(result.avatar_url);
    showToast("Đã cập nhật ảnh đại diện");
  } catch (error) { showToast(error.message); }
  finally { button.disabled = false; event.target.disabled = false; event.target.value = ""; }
});

document.getElementById("removeAvatarBtn").addEventListener("click", async event => {
  const button = event.currentTarget;
  const version = accountVersion;
  button.disabled = true;
  try {
    await api("/api/auth/avatar", {method: "DELETE"});
    if (version !== accountVersion) return;
    renderAvatar(null);
    showToast("Đã xóa ảnh đại diện");
  } catch (error) { showToast(error.message); }
  finally { button.disabled = false; }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  try {
    await api("/api/auth/logout", {method: "POST"});
    showAuth();
  } catch (error) { showToast(error.message); }
});

async function refreshGroups() {
  const version = accountVersion;
  const [groups, invitations] = await Promise.all([api("/api/groups"), api("/api/invitations")]);
  if (version !== accountVersion) return;
  const previous = ledgerPicker.value;
  familyGroups = groups;
  ledgerPicker.innerHTML = '<option value="">Cá nhân</option>' + groups.map(group =>
    `<option value="${group.id}">${html(group.name)}</option>`).join("");
  ledgerPicker.value = groups.some(group => String(group.id) === previous) ? previous : "";
  renderInvitations(invitations);
  await renderGroupDetails();
}

function renderInvitations(invitations, notify = false) {
  invitationRevision++;
  const snapshot = JSON.stringify(invitations);
  if (snapshot === invitationSnapshot) return;
  const previous = invitationSnapshot ? JSON.parse(invitationSnapshot) : [];
  const hasNew = invitations.some(item => !previous.some(old => old.group_id === item.group_id));
  invitationSnapshot = snapshot;
  document.getElementById("invitations").innerHTML = invitations.map(invitation => `
    <div class="invitation-row"><span>Lời mời tham gia <strong>${html(invitation.name)}</strong></span>
    <div class="toolbar"><button class="button secondary compact" data-accept="${invitation.group_id}">Chấp nhận</button>
    <button class="button ghost compact" data-decline="${invitation.group_id}">Từ chối</button></div></div>`).join("");
  if (notify && hasNew) showToast("Bạn có lời mời tham gia gia đình mới");
}

async function pollInvitations() {
  if (!invitationTimer || document.hidden || dashboard.classList.contains("hidden") || invitationPolling || invitationBusy) return;
  invitationPolling = true;
  const version = accountVersion;
  const revision = invitationRevision;
  try {
    const invitations = await api("/api/invitations", {cache: "no-store"});
    if (version !== accountVersion || revision !== invitationRevision || invitationBusy) return;
    renderInvitations(invitations, true);
  } catch (_) {
    // Retry on the next tick if the connection drops. api() handles expired sessions.
  } finally {
    invitationPolling = false;
  }
}

window.addEventListener("focus", pollInvitations);
document.addEventListener("visibilitychange", pollInvitations);

async function renderGroupDetails() {
  const group = selectedGroup();
  document.getElementById("groupDetails").classList.toggle("hidden", !group);
  document.getElementById("inviteForm").classList.toggle("hidden", !group?.is_owner);
  document.getElementById("incomeTitle").textContent = group ? "Thu nhập bạn góp vào gia đình" : "Thu nhập tháng";
  document.getElementById("incomeHint").classList.toggle("hidden", !group);
  document.getElementById("ledgerHint").textContent = group
    ? `Đang ghi vào ${group.name}. Thành viên xem được sổ chung; bạn chỉ sửa khoản chi của mình, chủ nhóm được quản lý toàn bộ.`
    : "Chỉ bạn xem được sổ cá nhân.";
  document.getElementById("clearBtn").classList.toggle("hidden", !!group && !group.is_owner);
  document.getElementById("memberList").innerHTML = "";
  if (!group) return;
  const version = accountVersion;
  const members = await api(`/api/groups/${group.id}/members`);
  if (version !== accountVersion || selectedGroup()?.id !== group.id) return;
  document.getElementById("memberList").innerHTML = members.map(member => `
    <div class="member-row"><div class="member-identity">
      <span class="member-avatar"><span>${html(member.username.slice(0, 1).toUpperCase())}</span>${member.avatar_url ? `<img src="${html(member.avatar_url)}?v=${Date.now()}" alt="" loading="lazy">` : ""}</span>
      <div class="member-info"><strong>${html(member.username)}</strong><small>${member.is_owner ? "Chủ nhóm" : "Thành viên"}</small></div>
    </div>
    ${group.is_owner && !member.is_owner ? `<button class="button danger compact" data-remove="${member.id}">Xóa khỏi nhóm</button>` : ""}</div>`).join("");
  document.querySelectorAll(".member-avatar img").forEach(image => {
    image.addEventListener("error", () => image.remove(), {once: true});
  });
}

ledgerPicker.addEventListener("change", async () => {
  loadVersion++;
  resetForm();
  expenseBody.innerHTML = "";
  breakdown.innerHTML = "";
  incomeInput.value = "";
  try { await Promise.all([renderGroupDetails(), loadAll()]); }
  catch (error) { showToast(error.message); }
});

document.getElementById("createGroupForm").addEventListener("submit", async event => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  try {
    const group = await api("/api/groups", {method: "POST", body: JSON.stringify({name: document.getElementById("groupNameInput").value.trim()})});
    await refreshGroups();
    ledgerPicker.value = String(group.id);
    resetForm();
    await Promise.all([renderGroupDetails(), loadAll()]);
    event.target.reset();
    showToast("Đã tạo nhóm gia đình");
  } catch (error) { showToast(error.message); }
  finally { button.disabled = false; }
});

document.getElementById("inviteForm").addEventListener("submit", async event => {
  event.preventDefault();
  const group = selectedGroup();
  if (!group) return;
  const button = event.submitter;
  button.disabled = true;
  try {
    await api(`/api/groups/${group.id}/invitations`, {method: "POST", body: JSON.stringify({username: document.getElementById("inviteUsernameInput").value.trim()})});
    event.target.reset();
    showToast("Đã gửi lời mời. Người nhận đăng nhập để chấp nhận.");
  } catch (error) { showToast(error.message); }
  finally { button.disabled = false; }
});

document.getElementById("invitations").addEventListener("click", async event => {
  const button = event.target.closest("button");
  if (!button) return;
  const groupId = button.dataset.accept || button.dataset.decline;
  if (!groupId || invitationBusy) return;
  invitationBusy = true;
  invitationRevision++;
  button.disabled = true;
  try {
    if (button.dataset.accept) await api(`/api/invitations/${groupId}/accept`, {method: "POST"});
    else await api(`/api/invitations/${groupId}`, {method: "DELETE"});
    await refreshGroups();
    if (button.dataset.accept) {
      ledgerPicker.value = groupId;
      resetForm();
      await renderGroupDetails();
    }
    await loadAll();
  } catch (error) { showToast(error.message); button.disabled = false; }
  finally { invitationBusy = false; invitationRevision++; }
});

document.getElementById("memberList").addEventListener("click", async event => {
  const button = event.target.closest("[data-remove]");
  const group = selectedGroup();
  if (!button || !group || !confirm("Xóa thành viên khỏi nhóm? Thu chi đã ghi vào sổ chung vẫn được giữ lại.")) return;
  try {
    await api(`/api/groups/${group.id}/members/${button.dataset.remove}`, {method: "DELETE"});
    await renderGroupDetails();
    showToast("Đã xóa thành viên");
  } catch (error) { showToast(error.message); }
});

document.getElementById("refreshGroupsBtn").addEventListener("click", async () => {
  try { await refreshGroups(); resetForm(); await loadAll(); }
  catch (error) { showToast(error.message); }
});

resetForm();
if (!(legacyRecovery.get("token") && ["reset", "verify"].includes(legacyRecovery.get("action")))) {
api("/api/auth/me").then(showDashboard).catch(error => {
  showAuth();
  if (error.message !== "Please log in") showToast(error.message);
});

}
