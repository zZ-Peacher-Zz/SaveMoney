async function api(url, options = {}) {
  const response = await fetch(url, {headers: {"Content-Type": "application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join("; ") : data.detail;
    const error = new Error(detail || "Có lỗi xảy ra, vui lòng thử lại.");
    error.details = data.detail;
    error.status = response.status;
    throw error;
  }
  return data;
}
