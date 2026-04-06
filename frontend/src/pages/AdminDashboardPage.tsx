import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useSession } from "../app/session";
import { fetchJson } from "../lib/api";

type AdminOverview = {
  title: string;
  pending_password_resets: number;
  user_count: number;
  last_refresh?: string | null;
  data_source: string;
  sync_supported: boolean;
  core_configured: boolean;
  admin_configured: boolean;
  sync_configured: boolean;
  core_missing: string[];
  admin_missing: string[];
  sync_missing: string[];
};
type AdminUser = { name?: string | null; email: string; role: string; region?: string | null };
type PendingPasswordReset = { id?: string | null; email: string; status: string; created_at?: string | null };
type SyncJobState = { job_id: string; status: string; progress: number; message: string; user_email?: string | null; region?: string | null; started_at?: number | null; ended_at?: number | null; error?: string | null };
type SyncPerformanceSummary = { latest_total_ms: number; latest_fetch_ms: number; latest_transform_ms: number; latest_upsert_ms: number; average_total_ms: number; recent_success_count: number; last_success_at?: string | null; last_sync_type?: string | null };
type AuditLogEntry = { created_at?: string | null; user_email?: string | null; action: string; region?: string | null; details?: Record<string, unknown> | unknown[] | string | null };
type CsvImportSummary = { people: number; organisations: number; events: number; payments: number; grants: number };
type AdminSectionProps = { title: string; badge: string; defaultOpen?: boolean; children: ReactNode };

const roleChoices = ["RPL", "ML", "Manager", "Admin", "Funder"] as const;

function AdminSection({ title, badge, defaultOpen = false, children }: AdminSectionProps) {
  return (
    <details className="section-card admin-collapsible" open={defaultOpen}>
      <summary className="admin-collapsible-summary">
        <div>
          <span className="badge">{badge}</span>
          <h2 className="card-title">{title}</h2>
        </div>
        <span className="admin-collapsible-arrow" aria-hidden="true">▹</span>
      </summary>
      <div className="admin-collapsible-content">{children}</div>
    </details>
  );
}

function formatAuditLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatAuditValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not provided";
  if (Array.isArray(value)) return value.length ? value.map((item) => formatAuditValue(item)).join(", ") : "None";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return "See related fields below";
  return String(value);
}

function flattenAuditDetails(value: unknown, prefix = ""): Array<{ label: string; value: string }> {
  if (value === null || value === undefined || value === "") {
    return prefix ? [{ label: formatAuditLabel(prefix), value: "Not provided" }] : [];
  }
  if (Array.isArray(value)) {
    if (!value.length) return prefix ? [{ label: formatAuditLabel(prefix), value: "None" }] : [];
    const primitiveOnly = value.every((item) => item === null || ["string", "number", "boolean"].includes(typeof item));
    if (primitiveOnly) {
      return [{ label: formatAuditLabel(prefix || "Details"), value: value.map((item) => formatAuditValue(item)).join(", ") }];
    }
    return value.flatMap((item, index) => flattenAuditDetails(item, prefix ? `${prefix} ${index + 1}` : `Item ${index + 1}`));
  }
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, nested]) => flattenAuditDetails(nested, prefix ? `${prefix} ${key}` : key));
  }
  return [{ label: formatAuditLabel(prefix || "Details"), value: formatAuditValue(value) }];
}

export function AdminDashboardPage() {
  const { user } = useSession();
  const queryClient = useQueryClient();
  const [createForm, setCreateForm] = useState({ name: "", email: "", password: "", roles: ["RPL"], region: "Global" });
  const [updateForm, setUpdateForm] = useState({ email: "", roles: ["RPL"], region: "Global", reason: "", confirmed: false });
  const [deleteForm, setDeleteForm] = useState({ email: "", reason: "", confirmed: false });
  const [resetForm, setResetForm] = useState({ email: "", newPassword: "" });
  const [tempResetForm, setTempResetForm] = useState({ email: "", temporaryPassword: "" });
  const [auditSearch, setAuditSearch] = useState("");
  const [auditAction, setAuditAction] = useState("");
  const [isAuditLogOpen, setIsAuditLogOpen] = useState(false);
  const [selectedAuditEntry, setSelectedAuditEntry] = useState<AuditLogEntry | null>(null);
  const [files, setFiles] = useState<{ people?: File | null; organisation?: File | null; event?: File | null; payment?: File | null; grant?: File | null }>({});

  const { data: overview, isLoading, error } = useQuery({ queryKey: ["admin", "overview"], queryFn: () => fetchJson<AdminOverview>("/admin/overview") });
  const { data: users } = useQuery({ queryKey: ["admin", "users"], queryFn: () => fetchJson<AdminUser[]>("/admin/users") });
  const { data: resetRequests } = useQuery({ queryKey: ["admin", "password-reset-requests"], queryFn: () => fetchJson<PendingPasswordReset[]>("/admin/password-reset-requests") });
  const { data: syncJob } = useQuery({
    queryKey: ["admin", "sync", "latest", user?.email],
    queryFn: () => fetchJson<SyncJobState | null>(`/admin/sync/latest${user?.email ? `?user_email=${encodeURIComponent(user.email)}` : ""}`),
    refetchInterval: (query) => {
      const state = query.state.data;
      return state && (state.status === "queued" || state.status === "running") ? 3000 : false;
    }
  });
  const { data: syncPerformance } = useQuery({ queryKey: ["admin", "sync", "performance"], queryFn: () => fetchJson<SyncPerformanceSummary>("/admin/sync/performance") });
  const { data: auditLogs } = useQuery({
    queryKey: ["admin", "audit", auditSearch, auditAction],
    queryFn: () => fetchJson<AuditLogEntry[]>(`/admin/audit-logs?limit=200${auditSearch ? `&search=${encodeURIComponent(auditSearch)}` : ""}${auditAction ? `&action=${encodeURIComponent(auditAction)}` : ""}`)
  });

  useEffect(() => {
    if (!users?.length) return;
    const currentUpdateUser = users.find((entry) => entry.email === updateForm.email) ?? users[0];
    if (currentUpdateUser && !updateForm.email) setUpdateForm({ email: currentUpdateUser.email, roles: currentUpdateUser.role.split(",").map((value) => value.trim()).filter(Boolean), region: currentUpdateUser.region ?? "Global", reason: "", confirmed: false });
    if (!deleteForm.email) setDeleteForm((current) => ({ ...current, email: users[0].email }));
    if (!resetForm.email) setResetForm((current) => ({ ...current, email: users[0].email }));
  }, [deleteForm.email, resetForm.email, updateForm.email, users]);

  const createUser = useMutation({
    mutationFn: () => fetchJson<AdminUser>("/admin/users", { method: "POST", body: JSON.stringify(createForm) }),
    onSuccess: () => {
      setCreateForm({ name: "", email: "", password: "", roles: ["RPL"], region: "Global" });
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    }
  });
  const updateUser = useMutation({
    mutationFn: () => fetchJson<AdminUser>(`/admin/users/${encodeURIComponent(updateForm.email)}`, { method: "PATCH", body: JSON.stringify(updateForm) }),
    onSuccess: () => {
      setUpdateForm((current) => ({ ...current, reason: "", confirmed: false }));
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    }
  });
  const deleteUser = useMutation({
    mutationFn: () => fetchJson<{ status: string }>(`/admin/users/${encodeURIComponent(deleteForm.email)}`, { method: "DELETE", body: JSON.stringify({ reason: deleteForm.reason, confirmed: deleteForm.confirmed }) }),
    onSuccess: () => {
      setDeleteForm({ email: "", reason: "", confirmed: false });
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    }
  });
  const resetPassword = useMutation({ mutationFn: () => fetchJson<{ status: string }>("/admin/users/reset-password", { method: "POST", body: JSON.stringify({ email: resetForm.email, new_password: resetForm.newPassword }) }), onSuccess: () => setResetForm((current) => ({ ...current, newPassword: "" })) });
  const completeReset = useMutation({
    mutationFn: () => fetchJson<{ status: string }>("/admin/password-reset-requests/complete", { method: "POST", body: JSON.stringify({ email: tempResetForm.email, temporary_password: tempResetForm.temporaryPassword }) }),
    onSuccess: () => {
      setTempResetForm({ email: "", temporaryPassword: "" });
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    }
  });
  const startSync = useMutation({ mutationFn: () => fetchJson<SyncJobState>("/admin/sync", { method: "POST", body: JSON.stringify({ user_email: user?.email ?? "System", region: user?.region ?? "Global" }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "sync"] }) });
  const stopSync = useMutation({ mutationFn: (jobId: string) => fetchJson<SyncJobState>(`/admin/sync/${jobId}/stop`, { method: "POST", body: JSON.stringify({ user_email: user?.email ?? "System", region: user?.region ?? "Global" }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "sync"] }) });
  const clearSync = useMutation({ mutationFn: (jobId: string) => fetchJson<SyncJobState>(`/admin/sync/${jobId}/clear`, { method: "POST", body: JSON.stringify({ user_email: user?.email ?? "System", region: user?.region ?? "Global" }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "sync"] }) });
  const importCsv = useMutation({
    mutationFn: () => {
      const formData = new FormData();
      if (files.people) formData.append("people_file", files.people);
      if (files.organisation) formData.append("organisation_file", files.organisation);
      if (files.event) formData.append("event_file", files.event);
      if (files.payment) formData.append("payment_file", files.payment);
      if (files.grant) formData.append("grant_file", files.grant);
      return fetchJson<CsvImportSummary>("/admin/imports/beacon-csv", { method: "POST", body: formData });
    },
    onSuccess: () => {
      setFiles({});
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    }
  });

  function handleCreateUser(event: FormEvent<HTMLFormElement>) { event.preventDefault(); createUser.mutate(); }
  function handleUpdateUser(event: FormEvent<HTMLFormElement>) { event.preventDefault(); updateUser.mutate(); }
  function handleDeleteUser(event: FormEvent<HTMLFormElement>) { event.preventDefault(); deleteUser.mutate(); }
  function handleResetPassword(event: FormEvent<HTMLFormElement>) { event.preventDefault(); resetPassword.mutate(); }
  function handleCompleteReset(event: FormEvent<HTMLFormElement>) { event.preventDefault(); completeReset.mutate(); }
  function handleCsvImport(event: FormEvent<HTMLFormElement>) { event.preventDefault(); importCsv.mutate(); }
  function toggleRole(currentRoles: string[], role: string) { return currentRoles.includes(role) ? currentRoles.filter((value) => value !== role) : [...currentRoles, role]; }
  function formatMs(value: number) { return `${(value / 1000).toFixed(1)}s`; }

  const auditActions = Array.from(new Set((auditLogs ?? []).map((item) => item.action))).sort();
  const selectedAuditDetails = selectedAuditEntry ? flattenAuditDetails(selectedAuditEntry.details) : [];
  const connectionChecks = [
    { label: "Core Supabase", configured: overview?.core_configured ?? false, missing: overview?.core_missing ?? [] },
    { label: "Admin Service Role", configured: overview?.admin_configured ?? false, missing: overview?.admin_missing ?? [] },
    { label: "Beacon Sync", configured: overview?.sync_configured ?? false, missing: overview?.sync_missing ?? [] }
  ];

  return (
    <section className="page">
      <div className="page-layout">
        <aside className="control-rail">
          <section className="control-panel">
            <span className="badge">Manual Sync</span>
            <div className="sidebar-meta-list">
              <div className="sidebar-meta-row"><span>Status</span><strong>{syncJob?.status ?? "idle"}</strong></div>
              <div className="sidebar-meta-row"><span>Progress</span><strong>{syncJob?.progress ?? 0}%</strong></div>
              <div className="sidebar-meta-row"><span>Last Success</span><strong>{syncPerformance?.last_success_at ?? "Unknown"}</strong></div>
            </div>
            <div className="meta-row">
              <button className="primary-button" type="button" onClick={() => startSync.mutate()} disabled={startSync.isPending}>{startSync.isPending ? "Starting..." : "Start Manual Sync"}</button>
              {syncJob?.job_id ? <button className="secondary-button" type="button" onClick={() => stopSync.mutate(syncJob.job_id)} disabled={stopSync.isPending || !["queued", "running"].includes(syncJob.status)}>{stopSync.isPending ? "Stopping..." : "Stop Sync"}</button> : null}
              {syncJob?.job_id ? <button className="secondary-button" type="button" onClick={() => clearSync.mutate(syncJob.job_id)} disabled={clearSync.isPending}>{clearSync.isPending ? "Clearing..." : "Clear Sync State"}</button> : null}
            </div>
          </section>

          <section className="control-panel">
            <span className="badge">Beacon CSV Upload</span>
            <form className="stack-form" onSubmit={handleCsvImport}>
              <label className="field-label"><span>People CSV</span><input type="file" accept=".csv" onChange={(event) => setFiles((current) => ({ ...current, people: event.target.files?.[0] ?? null }))} /></label>
              <label className="field-label"><span>Organisation CSV</span><input type="file" accept=".csv" onChange={(event) => setFiles((current) => ({ ...current, organisation: event.target.files?.[0] ?? null }))} /></label>
              <label className="field-label"><span>Event CSV</span><input type="file" accept=".csv" onChange={(event) => setFiles((current) => ({ ...current, event: event.target.files?.[0] ?? null }))} /></label>
              <label className="field-label"><span>Payment CSV</span><input type="file" accept=".csv" onChange={(event) => setFiles((current) => ({ ...current, payment: event.target.files?.[0] ?? null }))} /></label>
              <label className="field-label"><span>Grant CSV</span><input type="file" accept=".csv" onChange={(event) => setFiles((current) => ({ ...current, grant: event.target.files?.[0] ?? null }))} /></label>
              <button className="primary-button" type="submit" disabled={importCsv.isPending}>{importCsv.isPending ? "Importing..." : "Import Beacon Exports"}</button>
            </form>
            {importCsv.data ? <div className="meta-row"><span className="meta-pill">People: {importCsv.data.people}</span><span className="meta-pill">Organisations: {importCsv.data.organisations}</span><span className="meta-pill">Events: {importCsv.data.events}</span><span className="meta-pill">Payments: {importCsv.data.payments}</span><span className="meta-pill">Grants: {importCsv.data.grants}</span></div> : null}
            {importCsv.error instanceof Error ? <p className="status-panel status-error">{importCsv.error.message}</p> : null}
          </section>
        </aside>

        <div className="content-stack">
          <section className="hero-card">
            <span className="badge">Admin</span>
            <h1>{overview?.title ?? "Admin Dashboard"}</h1>
            <p>Admin workflows are now presented in a denser, Streamlit-style control and output layout.</p>
          </section>

          {isLoading ? <p className="status-panel">Loading admin overview...</p> : null}
          {error instanceof Error ? <p className="status-panel status-error">{error.message}</p> : null}

          <section className="metric-grid">
            <article className="metric-card"><span className="metric-label">Users</span><strong className="metric-value">{overview?.user_count ?? 0}</strong></article>
            <article className="metric-card"><span className="metric-label">Pending Resets</span><strong className="metric-value">{overview?.pending_password_resets ?? 0}</strong></article>
            <article className="metric-card"><span className="metric-label">Last Refresh</span><strong className="metric-value">{overview?.last_refresh ?? "Unknown"}</strong></article>
            <article className="metric-card"><span className="metric-label">Sync Supported</span><strong className="metric-value">{overview?.sync_supported ? "Yes" : "No"}</strong></article>
          </section>

          <section className="section-card">
            <span className="badge">Connection Status</span>
            <div className="metric-grid">
              {connectionChecks.map((check) => (
                <article key={check.label} className="metric-card">
                  <span className="metric-label">{check.label}</span>
                  <strong className="metric-value">{check.configured ? "Ready" : "Missing"}</strong>
                  <p>{check.configured ? "Configuration loaded in the backend process." : `Missing: ${check.missing.join(", ") || "Unknown setting"}`}</p>
                </article>
              ))}
            </div>
            <p>Data source: {overview?.data_source ?? "unknown"}.</p>
          </section>

          <section className="section-card">
            <span className="badge">Sync Performance</span>
            <div className="metric-grid">
              <article className="metric-card"><span className="metric-label">Total</span><strong className="metric-value">{formatMs(syncPerformance?.latest_total_ms ?? 0)}</strong></article>
              <article className="metric-card"><span className="metric-label">Fetch</span><strong className="metric-value">{formatMs(syncPerformance?.latest_fetch_ms ?? 0)}</strong></article>
              <article className="metric-card"><span className="metric-label">Transform</span><strong className="metric-value">{formatMs(syncPerformance?.latest_transform_ms ?? 0)}</strong></article>
              <article className="metric-card"><span className="metric-label">Upsert</span><strong className="metric-value">{formatMs(syncPerformance?.latest_upsert_ms ?? 0)}</strong></article>
            </div>
            {syncPerformance?.recent_success_count ? <p>Average total over last {syncPerformance.recent_success_count} successful syncs: {formatMs(syncPerformance.average_total_ms)}.{syncPerformance.last_sync_type ? ` Latest type: ${syncPerformance.last_sync_type}.` : ""}</p> : null}
            {syncJob?.error ? <p className="status-panel status-error">{syncJob.error}</p> : null}
          </section>

          <AdminSection title="Add User" badge="Create User">
            <form className="filter-grid" onSubmit={handleCreateUser}>
              <label className="field-label"><span>Name</span><input value={createForm.name} onChange={(event) => setCreateForm({ ...createForm, name: event.target.value })} /></label>
              <label className="field-label"><span>Email</span><input type="email" value={createForm.email} onChange={(event) => setCreateForm({ ...createForm, email: event.target.value })} required /></label>
              <label className="field-label"><span>Password</span><input type="password" value={createForm.password} onChange={(event) => setCreateForm({ ...createForm, password: event.target.value })} required /></label>
              <label className="field-label"><span>Region</span><input value={createForm.region} onChange={(event) => setCreateForm({ ...createForm, region: event.target.value })} /></label>
              <div className="field-label"><span>Roles</span><div className="checkbox-grid">{roleChoices.map((role) => <label key={role} className="checkbox-pill"><input type="checkbox" checked={createForm.roles.includes(role)} onChange={() => setCreateForm({ ...createForm, roles: toggleRole(createForm.roles, role) })} /><span>{role}</span></label>)}</div></div>
              <button className="primary-button" type="submit" disabled={createUser.isPending}>{createUser.isPending ? "Creating..." : "Create User"}</button>
            </form>
            {createUser.error instanceof Error ? <p className="status-panel status-error">{createUser.error.message}</p> : null}
          </AdminSection>

          <AdminSection title="Update User Access" badge="User Access">
            <form className="filter-grid" onSubmit={handleUpdateUser}>
              <label className="field-label"><span>User</span><select value={updateForm.email} onChange={(event) => { const selectedUser = (users ?? []).find((entry) => entry.email === event.target.value); setUpdateForm({ email: event.target.value, roles: selectedUser?.role.split(",").map((value) => value.trim()).filter(Boolean) ?? ["RPL"], region: selectedUser?.region ?? "Global", reason: "", confirmed: false }); }}><option value="">Select user</option>{(users ?? []).map((entry) => <option key={entry.email} value={entry.email}>{entry.email}</option>)}</select></label>
              <label className="field-label"><span>Region</span><input value={updateForm.region} onChange={(event) => setUpdateForm({ ...updateForm, region: event.target.value })} /></label>
              <label className="field-label"><span>Reason</span><input value={updateForm.reason} onChange={(event) => setUpdateForm({ ...updateForm, reason: event.target.value })} required /></label>
              <label className="field-label field-checkbox"><span>Confirm</span><input type="checkbox" checked={updateForm.confirmed} onChange={(event) => setUpdateForm({ ...updateForm, confirmed: event.target.checked })} /></label>
              <div className="field-label"><span>Roles</span><div className="checkbox-grid">{roleChoices.map((role) => <label key={role} className="checkbox-pill"><input type="checkbox" checked={updateForm.roles.includes(role)} onChange={() => setUpdateForm({ ...updateForm, roles: toggleRole(updateForm.roles, role) })} /><span>{role}</span></label>)}</div></div>
              <button className="primary-button" type="submit" disabled={updateUser.isPending || !updateForm.email}>{updateUser.isPending ? "Updating..." : "Update Access"}</button>
            </form>
            {updateUser.error instanceof Error ? <p className="status-panel status-error">{updateUser.error.message}</p> : null}
          </AdminSection>

          <AdminSection title="Password Reset" badge="Password Reset">
            <form className="filter-grid" onSubmit={handleResetPassword}>
              <label className="field-label"><span>Email</span><select value={resetForm.email} onChange={(event) => setResetForm({ ...resetForm, email: event.target.value })} required><option value="">Select user</option>{(users ?? []).map((entry) => <option key={entry.email} value={entry.email}>{entry.email}</option>)}</select></label>
              <label className="field-label"><span>New Password</span><input type="password" value={resetForm.newPassword} onChange={(event) => setResetForm({ ...resetForm, newPassword: event.target.value })} required /></label>
              <button className="primary-button" type="submit" disabled={resetPassword.isPending}>{resetPassword.isPending ? "Updating..." : "Reset Password"}</button>
            </form>
            {resetPassword.error instanceof Error ? <p className="status-panel status-error">{resetPassword.error.message}</p> : null}
          </AdminSection>

          <AdminSection title="Pending Reset Requests" badge="Password Requests">
            <form className="filter-grid" onSubmit={handleCompleteReset}>
              <label className="field-label"><span>Email</span><select value={tempResetForm.email} onChange={(event) => setTempResetForm({ ...tempResetForm, email: event.target.value })} required><option value="">Select request</option>{(resetRequests ?? []).map((request) => <option key={request.id ?? request.email} value={request.email}>{request.email}</option>)}</select></label>
              <label className="field-label"><span>Temporary Password</span><input type="password" value={tempResetForm.temporaryPassword} onChange={(event) => setTempResetForm({ ...tempResetForm, temporaryPassword: event.target.value })} required /></label>
              <button className="primary-button" type="submit" disabled={completeReset.isPending}>{completeReset.isPending ? "Applying..." : "Set Temporary Password"}</button>
            </form>
            {completeReset.error instanceof Error ? <p className="status-panel status-error">{completeReset.error.message}</p> : null}
          </AdminSection>

          <AdminSection title="Delete User" badge="Delete User">
            <form className="filter-grid" onSubmit={handleDeleteUser}>
              <label className="field-label"><span>User</span><select value={deleteForm.email} onChange={(event) => setDeleteForm({ ...deleteForm, email: event.target.value })} required><option value="">Select user</option>{(users ?? []).map((entry) => <option key={entry.email} value={entry.email}>{entry.email}</option>)}</select></label>
              <label className="field-label"><span>Reason</span><input value={deleteForm.reason} onChange={(event) => setDeleteForm({ ...deleteForm, reason: event.target.value })} required /></label>
              <label className="field-label field-checkbox"><span>Confirm</span><input type="checkbox" checked={deleteForm.confirmed} onChange={(event) => setDeleteForm({ ...deleteForm, confirmed: event.target.checked })} /></label>
              <button className="primary-button" type="submit" disabled={deleteUser.isPending}>{deleteUser.isPending ? "Deleting..." : "Delete User"}</button>
            </form>
            {deleteUser.error instanceof Error ? <p className="status-panel status-error">{deleteUser.error.message}</p> : null}
          </AdminSection>

          <AdminSection title="List Users" badge="Users">
            <div className="table-card">
              {users && users.length ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Roles</th>
                      <th>Region</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((entry) => (
                      <tr key={entry.email}>
                        <td>{entry.name ?? ""}</td>
                        <td>{entry.email}</td>
                        <td>{entry.role}</td>
                        <td>{entry.region ?? ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="status-panel status-error">
                  Supabase did not return any users. Verify `RPL_SUPABASE_URL`, `RPL_SUPABASE_KEY`, and `RPL_SUPABASE_SERVICE_ROLE_KEY` are set for the API service.
                </p>
              )}
            </div>
          </AdminSection>

          <section className="section-card">
            <span className="badge">System Audit Log</span>
            <p>Open the audit log in a focused view with search and readable detail formatting.</p>
            <div className="meta-row">
              <button className="primary-button" type="button" onClick={() => setIsAuditLogOpen(true)}>View Audit Log</button>
              <span className="meta-pill">{auditLogs?.length ?? 0} entries loaded</span>
            </div>
          </section>
        </div>
      </div>

      {isAuditLogOpen ? (
        <div className="modal-backdrop" role="presentation" onClick={() => setIsAuditLogOpen(false)}>
          <div className="modal-card modal-card-wide" role="dialog" aria-modal="true" aria-label="Audit log" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <span className="badge">Audit Log</span>
                <h2 className="card-title">System audit log</h2>
              </div>
              <button className="secondary-button" type="button" onClick={() => setIsAuditLogOpen(false)}>Close</button>
            </div>
            <div className="filter-grid">
              <label className="field-label"><span>Search</span><input value={auditSearch} onChange={(event) => setAuditSearch(event.target.value)} placeholder="User, action, or details" /></label>
              <label className="field-label"><span>Action</span><select value={auditAction} onChange={(event) => setAuditAction(event.target.value)}><option value="">All</option>{auditActions.map((action) => <option key={action} value={action}>{action}</option>)}</select></label>
            </div>
            <div className="audit-log-list">
              {(auditLogs ?? []).map((entry, index) => (
                <button key={`${entry.created_at ?? "log"}-${entry.action}-${index}`} className="audit-log-item" type="button" onClick={() => setSelectedAuditEntry(entry)}>
                  <div className="audit-log-item-top">
                    <strong>{entry.action}</strong>
                    <span>{entry.created_at ?? "Unknown time"}</span>
                  </div>
                  <div className="audit-log-item-meta">
                    <span>User: {entry.user_email ?? "System"}</span>
                    <span>Region: {entry.region ?? "Global"}</span>
                  </div>
                  <p className="audit-log-item-preview">
                    {selectedAuditEntry === entry ? "Currently open" : (flattenAuditDetails(entry.details)[0]?.value ?? "Open to view details")}
                  </p>
                </button>
              ))}
              {!auditLogs?.length ? <p className="status-panel">No audit entries matched the current filters.</p> : null}
            </div>
          </div>
        </div>
      ) : null}

      {selectedAuditEntry ? (
        <div className="modal-backdrop" role="presentation" onClick={() => setSelectedAuditEntry(null)}>
          <div className="modal-card" role="dialog" aria-modal="true" aria-label="Audit log detail" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <span className="badge">Audit Entry</span>
                <h2 className="card-title">{selectedAuditEntry.action}</h2>
              </div>
              <button className="secondary-button" type="button" onClick={() => setSelectedAuditEntry(null)}>Close</button>
            </div>
            <div className="audit-detail-grid">
              <div className="audit-detail-block"><span className="metric-label">When</span><strong>{selectedAuditEntry.created_at ?? "Unknown"}</strong></div>
              <div className="audit-detail-block"><span className="metric-label">User</span><strong>{selectedAuditEntry.user_email ?? "System"}</strong></div>
              <div className="audit-detail-block"><span className="metric-label">Region</span><strong>{selectedAuditEntry.region ?? "Global"}</strong></div>
            </div>
            <div className="audit-detail-list">
              {selectedAuditDetails.length ? selectedAuditDetails.map((item) => (
                <div key={`${item.label}-${item.value}`} className="audit-detail-row">
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              )) : <p className="status-panel">No additional details were recorded for this entry.</p>}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
