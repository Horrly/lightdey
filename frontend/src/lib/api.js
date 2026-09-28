import { deviceId } from "./local";

export class ApiError extends Error {
  constructor(status, data) {
    super(firstErrorMessage(data) || `Request failed (${status})`);
    this.status = status;
    this.data = data;
  }
}

export function firstErrorMessage(data) {
  if (!data || typeof data !== "object") return null;
  if (typeof data.detail === "string") return data.detail;
  for (const [field, value] of Object.entries(data)) {
    const msg = Array.isArray(value) ? value[0] : value;
    if (typeof msg === "string") return field === "non_field_errors" ? msg : `${field}: ${msg}`;
  }
  return null;
}

export async function api(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: { "Content-Type": "application/json", "X-Device-Id": deviceId() },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, { detail: "You seem to be offline. Check your connection and try again." });
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}
