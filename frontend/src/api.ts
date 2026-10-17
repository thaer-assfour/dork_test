// Thin typed API client for the DorkHub backend.

export type Program = {
  id: number;
  name: string;
  homepage: string | null;
  policy_url: string | null;
  contact_url: string | null;
  source: string;
  offers_bounty: boolean | null;
  bounty_confidence: number;
  status: string;
  notes: string | null;
  discovered_at: string;
};

export type Target = {
  id: number;
  program_id: number | null;
  value: string;
  kind: string;
  in_scope: boolean;
  approved: boolean;
  notes: string | null;
  added_at: string;
};

export type Dork = {
  id: number;
  category: string;
  name: string;
  template: string;
  priority: number;
  enabled: boolean;
  mergeable: boolean;
  merge_group: string | null;
  description: string | null;
};

export type EngineInfo = {
  name: string;
  price_per_1000: number;
  free_quota: number;
  configured: boolean;
  is_default: boolean;
};

export type Estimate = {
  engine: string;
  raw_count: number;
  merged_count: number;
  billable_count: number;
  cached_count: number;
  estimated_cost: number;
  warn: boolean;
};

export type Scan = {
  id: number;
  created_at: string;
  engine_name: string;
  status: string;
  estimated_queries: number;
  estimated_cost: number;
  actual_queries: number;
  actual_cost: number;
};

export type ResultRow = {
  id: number;
  target_id: number;
  url: string;
  title: string | null;
  snippet: string | null;
  label: string;
  notes: string | null;
  seen_count: number;
  first_seen: string;
  last_seen: string;
};

export type Coverage = {
  targets: { id: number; value: string }[];
  dorks: { id: number; name: string; category: string }[];
  cells: {
    target_id: number;
    dork_id: number | null;
    last_scanned: string | null;
    result_count: number;
    scan_count: number;
  }[];
};

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (res.status === 401) throw new Error("unauthorized");
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  authStatus: () => req<{ auth_required: boolean }>("/auth/status"),
  login: (password: string) =>
    req<{ ok: boolean }>("/auth/login", { method: "POST", body: JSON.stringify({ password }) }),
  logout: () => req<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  dashboard: () => req<Record<string, number>>("/dashboard"),
  engines: () => req<EngineInfo[]>("/engines"),

  discover: (source: string, only_self_hosted = true) =>
    req<{ fetched: number; added: number }>("/discovery/run", {
      method: "POST",
      body: JSON.stringify({ source, only_self_hosted }),
    }),
  addManual: (body: Record<string, unknown>) =>
    req<Program>("/discovery/manual", { method: "POST", body: JSON.stringify(body) }),
  programs: (status?: string, q?: string) => {
    const p = new URLSearchParams();
    if (status) p.set("status", status);
    if (q) p.set("q", q);
    return req<Program[]>(`/programs?${p.toString()}`);
  },
  setProgramStatus: (id: number, status: string) =>
    req<Program>(`/programs/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),

  targets: (approved?: boolean) =>
    req<Target[]>(`/targets${approved === undefined ? "" : `?approved=${approved}`}`),
  createTarget: (body: Record<string, unknown>) =>
    req<Target>("/targets", { method: "POST", body: JSON.stringify(body) }),
  approveTarget: (id: number, approved: boolean) =>
    req<Target>(`/targets/${id}/approve`, { method: "PATCH", body: JSON.stringify({ approved }) }),
  deleteTarget: (id: number) => req<{ ok: boolean }>(`/targets/${id}`, { method: "DELETE" }),

  dorks: () => req<Dork[]>("/dorks"),
  toggleDork: (id: number, enabled: boolean) =>
    req<Dork>(`/dorks/${id}/toggle`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  importDorks: () => req<{ added: number; updated: number }>("/dorks/import", { method: "POST" }),

  estimate: (target_ids: number[], dork_ids: number[], engine: string) =>
    req<Estimate>("/scans/estimate", {
      method: "POST",
      body: JSON.stringify({ target_ids, dork_ids, engine }),
    }),
  runScan: (target_ids: number[], dork_ids: number[], engine: string) =>
    req<Scan>("/scans/run", {
      method: "POST",
      body: JSON.stringify({ target_ids, dork_ids, engine }),
    }),
  scans: () => req<Scan[]>("/scans"),
  scan: (id: number) => req<Scan>(`/scans/${id}`),

  coverage: () => req<Coverage>("/coverage"),
  results: (target_id?: number, label?: string) => {
    const p = new URLSearchParams();
    if (target_id) p.set("target_id", String(target_id));
    if (label) p.set("label", label);
    return req<ResultRow[]>(`/results?${p.toString()}`);
  },
  labelResult: (id: number, label: string, notes?: string) =>
    req<ResultRow>(`/results/${id}`, { method: "PATCH", body: JSON.stringify({ label, notes }) }),
};
