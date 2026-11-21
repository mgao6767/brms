// JSON API client.

async function request(method, url, body) {
  const options = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(url, options);
  if (response.status === 204) return null;
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    if (data && typeof data === "object" && data.detail !== undefined) {
      message = Array.isArray(data.detail)
        ? data.detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("\n")
        : String(data.detail);
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

export const api = {
  banks: () => request("GET", "/api/banks"),
  bank: (id) => request("GET", `/api/banks/${encodeURIComponent(id)}`),
  createBank: (bank) => request("POST", "/api/banks", { bank }),
  callReport: (body) => request("POST", "/api/banks/call-report", body),
  deleteBank: (id) => request("DELETE", `/api/banks/${encodeURIComponent(id)}`),
  scenarios: () => request("GET", "/api/scenarios"),
  runs: () => request("GET", "/api/runs"),
  run: (id) => request("GET", `/api/runs/${encodeURIComponent(id)}`),
  createRun: (body) => request("POST", "/api/runs", body),
  deleteRun: (id) => request("DELETE", `/api/runs/${encodeURIComponent(id)}`),
  day: (id, date) => request("GET", `/api/runs/${encodeURIComponent(id)}/day?date=${encodeURIComponent(date)}`),
  metricsCsvUrl: (id) => `/api/runs/${encodeURIComponent(id)}/metrics.csv`,
  tableCsvUrl: (id, table) => `/api/runs/${encodeURIComponent(id)}/${table}.csv`,
};
