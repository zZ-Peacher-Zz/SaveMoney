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
let historyItems = [];
const historyFilters = document.getElementById("historyFilters");
const historySearch = document.getElementById("historySearch");
const historyCategory = document.getElementById("historyCategory");
const historyFrom = document.getElementById("historyFrom");
const historyTo = document.getElementById("historyTo");
const historyFilterStatus = document.getElementById("historyFilterStatus");
let historyScope = "";
const collapsedHistoryDays = new Set();
let dashboardSnapshot = "";
let ledgerTimer = null;
let ledgerPolling = false;

function normalizeSearch(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\u0111/g, "d").replace(/\u0110/g, "D").toLocaleLowerCase("vi");
}

function updateHistory(items) {
  const scope = `${monthPicker.value}:${ledgerPicker.value}`;
  if (scope !== historyScope) {
    historyFilters.reset();
    collapsedHistoryDays.clear();
  }
  historyScope = scope;
  historyItems = items;
  const category = historyCategory.value;
  const categories = [...new Set(items.map(item => item.category))].sort((a, b) => a.localeCompare(b, "vi"));
  historyCategory.innerHTML = '<option value="">T\u1ea5t c\u1ea3 danh m\u1ee5c</option>' + categories.map(value => `<option value="${html(value)}">${html(value)}</option>`).join("");
  historyCategory.value = categories.includes(category) ? category : "";
  const [year, month] = monthPicker.value.split("-").map(Number);
  const end = new Date(year, month, 0).getDate();
  for (const input of [historyFrom, historyTo]) {
    input.min = `${monthPicker.value}-01`;
    input.max = `${monthPicker.value}-${end}`;
  }
  filterHistory();
}

function filterHistory() {
  const query = normalizeSearch(historySearch.value.trim());
  const invalidRange = historyFrom.value && historyTo.value && historyFrom.value > historyTo.value;
  const filtered = invalidRange ? [] : historyItems.filter(item =>
    (!historyCategory.value || item.category === historyCategory.value) &&
    (!historyFrom.value || item.expense_date >= historyFrom.value) &&
    (!historyTo.value || item.expense_date <= historyTo.value) &&
    (!query || normalizeSearch([item.note, item.category, item.username].join(" ")).includes(query)));
  renderExpenses(filtered);
  const total = filtered.reduce((sum, item) => sum + Number(item.amount), 0);
  historyFilterStatus.textContent = invalidRange
    ? "Ng\u00e0y b\u1eaft \u0111\u1ea7u ph\u1ea3i tr\u01b0\u1edbc ho\u1eb7c b\u1eb1ng ng\u00e0y k\u1ebft th\u00fac."
    : `${filtered.length}/${historyItems.length} giao d\u1ecbch \u00b7 T\u1ed5ng k\u1ebft qu\u1ea3: ${money(total)}`;
  if (!filtered.length) {
    emptyState.querySelector("strong").textContent = historyItems.length ? "Kh\u00f4ng c\u00f3 k\u1ebft qu\u1ea3 ph\u00f9 h\u1ee3p" : "Ch\u01b0a c\u00f3 kho\u1ea3n chi";
    emptyState.querySelector("span").textContent = historyItems.length ? "Th\u1eed \u0111\u1ed5i ho\u1eb7c x\u00f3a b\u1ed9 l\u1ecdc." : "Th\u00eam giao d\u1ecbch \u0111\u1ea7u ti\u00ean \u0111\u1ec3 b\u1eaft \u0111\u1ea7u theo d\u00f5i th\u00e1ng n\u00e0y.";
  }
}
historyFilters.addEventListener("submit", event => {
  event.preventDefault();
  filterHistory();
  if (historyFrom.value && historyTo.value && historyFrom.value > historyTo.value) {
    FieldErrors.set(historyTo, "Ng\u00e0y k\u1ebft th\u00fac ph\u1ea3i t\u1eeb ng\u00e0y b\u1eaft \u0111\u1ea7u tr\u1edf \u0111i.");
    historyTo.focus();
    return;
  }
  document.getElementById("historyFilterDialog").close();
});
historySearch.addEventListener("input", filterHistory);
for (const input of [historyCategory, historyFrom, historyTo]) input.addEventListener("change", filterHistory);
document.getElementById("clearHistoryFilters").addEventListener("click", () => {
  historyFilters.reset();
  filterHistory();
});

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
    let details;
    try {
      const data = await response.json();
      message = data.detail || message;
      details = data.detail;
    } catch (_) {}
    if (response.status === 401) showAuth();
    if (Array.isArray(message)) message = message.map(item => item.msg).join("; ");
    const error = new Error(message);
    error.details = details;
    error.status = response.status;
    throw error;
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

function setDashboardLoading(loading, error = "") {
  const container = document.getElementById("dashboard");
  container.classList.toggle("is-loading", loading);
  container.classList.toggle("load-failed", Boolean(error));
  container.setAttribute("aria-busy", String(loading));
  const message = document.getElementById("dashboardLoadMessage");
  message.textContent = error || (loading ? "\u0110ang t\u1ea3i d\u1eef li\u1ec7u..." : "\u0110\u00e3 t\u1ea3i d\u1eef li\u1ec7u.");
  message.classList.toggle("sr-only", !error);
  document.getElementById("retryDashboard").classList.toggle("hidden", !error);
}

async function loadAll({background = false} = {}) {
  const requestVersion = ++loadVersion;
  const version = accountVersion;
  const month = monthPicker.value;
  const ledger = ledgerPicker.value;
  if (!background) setDashboardLoading(true);
  try {
    const [summary, expenses] = await Promise.all([
      api(`/api/months/${month}/summary`, {cache: "no-store"}),
      api(`/api/months/${month}/expenses`, {cache: "no-store"})
    ]);
    if (version !== accountVersion || requestVersion !== loadVersion || month !== monthPicker.value || ledger !== ledgerPicker.value) return;
    const snapshot = JSON.stringify([month, ledger, summary, expenses]);
    if (!background || snapshot !== dashboardSnapshot) {
      renderSummary(summary);
      renderBreakdown(summary);
      updateHistory(expenses);
      dashboardSnapshot = snapshot;
    }
    // Background updates must not replace a contribution the user is typing.
    if (!background) MoneyInput.set(incomeInput, summary.my_income || "");
    document.getElementById("exportBtn").href = ledgerUrl(`/api/months/${month}/export.csv`);
    setDashboardLoading(false);
  } catch (error) {
    if (!background && version === accountVersion && requestVersion === loadVersion) setDashboardLoading(false, error.message);
    throw error;
  }
}

async function pollLedger() {
  if (!ledgerTimer || document.hidden || !ledgerPicker.value || ledgerPolling ||
      dashboard.classList.contains("hidden") || dashboard.getAttribute("aria-busy") === "true") return;
  ledgerPolling = true;
  try {
    await loadAll({background: true});
  } catch (_) {
    // Keep the current data during network failures; retry on the next tick.
  } finally {
    ledgerPolling = false;
  }
}

window.addEventListener("focus", pollLedger);
window.addEventListener("online", pollLedger);
document.addEventListener("visibilitychange", pollLedger);

async function initializeDashboardData() {
  setDashboardLoading(true);
  try {
    await refreshGroups();
    await loadAll();
  } catch (error) {
    setDashboardLoading(false, error.message);
  }
}
document.getElementById("retryDashboard").addEventListener("click", initializeDashboardData);

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
      <th colspan="6">
        <button type="button" class="day-summary day-toggle" data-day="${day}" aria-expanded="${!collapsedHistoryDays.has(day)}" aria-controls="${expenses.map(item => `history-expense-${item.id}`).join(" ")}">
          <span class="day-copy"><span>${formatDate(day)}</span><small>${expenses.length} khoản chi</small></span>
          <span class="day-total">${money(total)}</span>
          <svg class="day-chevron" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
        </button>
      </th>
    </tr>
    ${expenses.map(item => `
    <tr id="history-expense-${item.id}" data-expense-day="${day}"${collapsedHistoryDays.has(day) ? " hidden" : ""}>
      <td data-label="Ng\u00e0y">${formatDate(item.expense_date)}</td>
      <td data-label="Ph\u00e2n lo\u1ea1i"><span class="tag">${html(item.category)}</span></td>
      <td class="expense-author" data-label="Ng\u01b0\u1eddi chi">${html(item.username || document.getElementById("currentUser").textContent)}</td>
      <td class="expense-note" data-label="Ghi ch\u00fa">${html(item.note || "—")}</td>
      <td class="amount" data-label="S\u1ed1 ti\u1ec1n">${money(item.amount)}</td>
      <td data-label="Thao t\u00e1c">
        <div class="row-actions">
          ${item.can_edit ? `<button type="button" class="icon-button history-icon edit" data-action="edit" data-id="${item.id}" aria-label="S&#7917;a kho&#7843;n chi" title="S&#7917;a kho&#7843;n chi"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m16 3 5 5-12 12-6 1 1-6L16 3Z"/><path d="m14 5 5 5"/></svg></button>
          <button type="button" class="icon-button history-icon delete" data-action="delete" data-id="${item.id}" aria-label="X&#243;a kho&#7843;n chi" title="X&#243;a kho&#7843;n chi"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/></svg></button>` : ""}
        </div>
      </td>
    </tr>
    `).join("")}`;
  }).join("");

  expenseBody.querySelectorAll(".day-toggle").forEach(button => {
    button.addEventListener("click", () => {
      const day = button.dataset.day;
      const collapsed = !collapsedHistoryDays.has(day);
      if (collapsed) collapsedHistoryDays.add(day);
      else collapsedHistoryDays.delete(day);
      button.setAttribute("aria-expanded", String(!collapsed));
      expenseBody.querySelectorAll("[data-expense-day]").forEach(row => {
        if (row.dataset.expenseDay === day) row.hidden = collapsed;
      });
    });
  });

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
  MoneyInput.set(amountInput, item.amount);
  noteInput.value = item.note || "";

  document.getElementById("formTitle").textContent = "Sửa khoản chi";
  document.getElementById("submitBtn").textContent = "Lưu thay đổi";
  cancelEditBtn.classList.remove("hidden");

  expenseForm.scrollIntoView({ behavior: "smooth", block: "center" });
  amountInput.focus({ preventScroll: true });
}

async function deleteExpense(id) {
  if (!await confirmDelete("Xóa khoản chi này khỏi lịch sử chi tiêu?")) return;

  try {
    await api(`/api/expenses/${id}`, { method: "DELETE" });
    await loadAll();
    showToast("Đã xoá khoản chi");
  } catch (error) {
    showToast(error.message);
  }
}

document.getElementById("incomeForm").addEventListener("submit", async event => {
  event.preventDefault();
  if (!FieldErrors.validate(incomeInput)) return;
  const button = document.getElementById("saveIncomeBtn");
  button.disabled = true;
  try {
    await api(`/api/months/${monthPicker.value}/income`, {
      method: "PUT",
      body: JSON.stringify({
        amount: MoneyInput.parse(incomeInput)
      })
    });

    document.getElementById("incomeDialog").close();
    await loadAll();
    showToast("Đã cập nhật thu nhập");
  } catch (error) {
    FieldErrors.report(error, {amount:incomeInput}, incomeInput);
  } finally { button.disabled = false; }
});

expenseForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (!FieldErrors.validate(expenseForm)) return;

  if (!dateInput.value.startsWith(monthPicker.value)) {
    FieldErrors.set(dateInput, "Ng\u00e0y chi ti\u00eau ph\u1ea3i thu\u1ed9c th\u00e1ng \u0111ang ch\u1ecdn.");
    dateInput.focus();
    return;
  }

  const payload = {
    expense_date: dateInput.value,
    category: categoryInput.value,
    amount: MoneyInput.parse(amountInput),
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
    FieldErrors.report(error, {expense_date:dateInput,category:categoryInput,amount:amountInput,note:noteInput}, amountInput);
  }
});

cancelEditBtn.addEventListener("click", resetForm);

monthPicker.addEventListener("change", async () => {
  resetForm();
  try { await loadAll(); } catch (error) { showToast(error.message); }
});

document.getElementById("clearBtn").addEventListener("click", async () => {
  if (!await confirmDelete("Xóa toàn bộ thu nhập và chi tiêu của tháng đang chọn trong sổ này?")) return;

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
  clearInterval(ledgerTimer);
  ledgerTimer = null;
  location.replace("/login" + location.hash);
}

async function showDashboard(user) {
  document.getElementById("currentUser").textContent = user.username;
  document.getElementById("avatarInitial").textContent = user.username.slice(0, 1).toUpperCase();
  renderAvatar(user.avatar_url);
  resetForm();
  await initializeDashboardData();
  clearInterval(invitationTimer);
  invitationTimer = setInterval(pollInvitations, 3000);
  clearInterval(ledgerTimer);
  ledgerTimer = setInterval(pollLedger, 5000);
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
  if (!await confirmDelete("Xóa ảnh đại diện của bạn?")) return;
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
  document.dispatchEvent(new CustomEvent("family-ledger-changed", {detail: group}));
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
    <div class="member-row" data-presence-user="${member.id}"><div class="member-identity">
      <span class="member-avatar"><span>${html(member.username.slice(0, 1).toUpperCase())}</span>${member.avatar_url ? `<img src="${html(member.avatar_url)}?v=${Date.now()}" alt="" loading="lazy">` : ""}</span>
      <div class="member-info"><strong>${html(member.username)}</strong><small>${member.is_owner ? "Chủ nhóm" : "Thành viên"}</small></div>
    </div>
    ${group.is_owner && !member.is_owner ? `<button class="button danger compact" data-remove="${member.id}">Xóa khỏi nhóm</button>` : ""}</div>`).join("");
  document.dispatchEvent(new Event("family-members-rendered"));
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
  if (!FieldErrors.validate(event.target)) return;
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
  } catch (error) { FieldErrors.report(error, {name:document.getElementById("groupNameInput")}, document.getElementById("groupNameInput")); }
  finally { button.disabled = false; }
});

document.getElementById("inviteForm").addEventListener("submit", async event => {
  event.preventDefault();
  if (!FieldErrors.validate(event.target)) return;
  const group = selectedGroup();
  if (!group) return;
  const button = event.submitter;
  button.disabled = true;
  try {
    await api(`/api/groups/${group.id}/invitations`, {method: "POST", body: JSON.stringify({username: document.getElementById("inviteUsernameInput").value.trim()})});
    event.target.reset();
    showToast("Đã gửi lời mời. Người nhận đăng nhập để chấp nhận.");
  } catch (error) { FieldErrors.report(error, {username:document.getElementById("inviteUsernameInput")}, document.getElementById("inviteUsernameInput")); }
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
  if (!button || !group) return;
  if (!await confirmDelete("Xóa thành viên khỏi nhóm? Thu chi đã ghi vào sổ chung vẫn được giữ lại.")) return;
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
api("/api/auth/me").then(showDashboard).catch(error => {
  showAuth();
  if (error.message !== "Please log in") showToast(error.message);
});
