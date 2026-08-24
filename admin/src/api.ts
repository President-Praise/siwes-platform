export type OrderStatus =
  | "pending" | "pending_payment" | "awaiting_details" | "generating" | "generated" | "failed";

export interface School {
  id: number;
  slug: string;
  name: string;
  full_name: string;
  logo_path: string | null;
  referral_prefix: string;
  paystack_secret_key: string | null;
  paystack_public_key: string | null;
  platform_cut_pct: number;
  active: number;
  created_at: string;
}

export interface SchoolAdmin {
  id: number;
  created_at: string;
  school_id: number;
  username: string;
  display_name: string | null;
  active: number;
}

export interface Order {
  id: number;
  school_id: number;
  created_at: string;
  matric_no: string;
  student_name: string;
  student_email: string | null;
  package: string | null;
  amount: number | null;
  platform_amount: number;
  admin_amount: number;
  express: number;
  priority: number;
  status: OrderStatus;
  reference: string | null;
  form_token: string | null;
  docx_path: string | null;
  pptx_path: string | null;
  error_message: string | null;
  delivered_at: string | null;
  printed_at: string | null;
  notes: string | null;
  test_mode: number;
  referral_code: string | null;
  referral_code_used: string | null;
  referral_discount: number;
  referral_credit_applied: number;
  payload_json: string;
}

export interface RevenueSummary {
  gross: number; platform: number; admin: number; count: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (r.status === 401) {
    throw new ApiError("unauthorized", 401);
  }
  if (!r.ok) {
    let detail: string;
    try { detail = (await r.json()).detail || r.statusText; } catch { detail = r.statusText; }
    throw new ApiError(detail, r.status);
  }
  if (r.headers.get("content-type")?.includes("application/json")) return r.json();
  return (await r.text()) as unknown as T;
}

export class ApiError extends Error {
  status: number;
  constructor(msg: string, status: number) { super(msg); this.status = status; }
}

// ---- Auth ----
export const api = {
  login(username: string, pin: string) {
    return request<{ role: string; school_id?: number; school_slug?: string; display_name?: string }>(
      "/admin/api/auth/login",
      { method: "POST", body: JSON.stringify({ username, pin }) },
    );
  },
  logout() { return request("/admin/api/auth/logout", { method: "POST" }); },
  me() {
    return request<{
      role: "super_admin" | "school_admin";
      school?: { id: number; slug: string; name: string; full_name: string };
      admin?: { id: number; username: string; display_name: string | null };
      super_admin_set?: boolean;
    }>("/admin/api/auth/me");
  },
  changePin(old_pin: string, new_pin: string) {
    return request("/admin/api/auth/change-pin", {
      method: "POST",
      body: JSON.stringify({ old_pin, new_pin }),
    });
  },

  // ---- Super admin ----
  superDashboard() { return request<any>("/admin/api/super/dashboard"); },
  superListSchools() { return request<School[]>("/admin/api/super/schools"); },
  superCreateSchool(data: any) { return request<{ id: number; school: School }>("/admin/api/super/schools", { method: "POST", body: JSON.stringify(data) }); },
  superGetSchool(id: number) { return request<any>(`/admin/api/super/schools/${id}`); },
  superUpdateSchool(id: number, data: any) { return request<any>(`/admin/api/super/schools/${id}`, { method: "PUT", body: JSON.stringify(data) }); },
  superUploadLogo(id: number, file: File) {
    const fd = new FormData(); fd.append("file", file);
    return fetch(`/admin/api/super/schools/${id}/logo`, { method: "POST", body: fd, credentials: "include" }).then(r => r.json());
  },
  superListAdmins(school_id: number) { return request<SchoolAdmin[]>(`/admin/api/super/schools/${school_id}/admins`); },
  superCreateAdmin(school_id: number, data: any) { return request<{ id: number }>(`/admin/api/super/schools/${school_id}/admins`, { method: "POST", body: JSON.stringify(data) }); },
  superUpdateAdmin(admin_id: number, data: any) { return request(`/admin/api/super/admins/${admin_id}`, { method: "PUT", body: JSON.stringify(data) }); },
  superAllOrders(params: Record<string, any> = {}) {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "").map(([k, v]) => [k, String(v)])).toString();
    return request<Order[]>(`/admin/api/super/orders${q ? "?" + q : ""}`);
  },
  superRevenue(days = 30) { return request<any>(`/admin/api/super/revenue?days=${days}`); },

  // ---- School admin ----
  schoolDashboard() { return request<any>("/admin/api/school/dashboard"); },
  schoolOrders(params: Record<string, any> = {}) {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "").map(([k, v]) => [k, String(v)])).toString();
    return request<Order[]>(`/admin/api/school/orders${q ? "?" + q : ""}`);
  },
  schoolOrderDetail(id: number) { return request<any>(`/admin/api/school/orders/${id}`); },
  schoolRetry(id: number) { return request(`/admin/api/school/orders/${id}/retry`, { method: "POST" }); },
  schoolDeliver(id: number) { return request(`/admin/api/school/orders/${id}/deliver`, { method: "POST" }); },
  schoolMarkPrinted(id: number) { return request(`/admin/api/school/orders/${id}/mark-printed`, { method: "POST" }); },
  schoolUpdateNotes(id: number, notes: string) { return request(`/admin/api/school/orders/${id}/notes`, { method: "POST", body: JSON.stringify({ notes }) }); },
  schoolStudents() { return request<any[]>("/admin/api/school/students"); },
  schoolAnalytics(days = 30) { return request<any>(`/admin/api/school/analytics?days=${days}`); },
  schoolSettings() { return request<any>("/admin/api/school/settings"); },
  schoolUpdateSettings(data: any) { return request<any>("/admin/api/school/settings", { method: "PUT", body: JSON.stringify(data) }); },
  schoolUpdatePrices(prices: any) { return request<any>("/admin/api/school/prices", { method: "PUT", body: JSON.stringify({ prices }) }); },
  schoolUploadLogo(file: File) {
    const fd = new FormData(); fd.append("file", file);
    return fetch("/admin/api/school/logo", { method: "POST", body: fd, credentials: "include" }).then(r => r.json());
  },
  schoolPrintQueue() { return request<Order[]>("/admin/api/school/print-queue"); },
  schoolExportUrl: "/admin/api/school/export",
};

export function fmtNaira(n: number | null | undefined): string {
  return "₦" + (n ?? 0).toLocaleString();
}

export function fmtDate(iso: string | null, withTime = false): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return withTime ? d.toLocaleString() : d.toLocaleDateString();
}
