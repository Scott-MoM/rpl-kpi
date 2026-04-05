import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { fetchJson } from "../lib/api";

type DashboardMetric = { label: string; value: string | number; description?: string | null };
type DashboardSection = { title: string; metrics: DashboardMetric[] };
type DashboardPayload = { title: string; region: string; timeframe: string; source: string; metrics: DashboardMetric[]; sections: DashboardSection[] };
type DashboardFilterOptions = { regions: string[] };
type DashboardDetailRow = { id: string; label: string; date?: string | null; region?: string | null; value?: string | number | null; metadata: Record<string, string | number | boolean | null> };
type DashboardDetailPayload = { section: string; region: string; timeframe: string; rows: DashboardDetailRow[] };
type MLEventDetailPayload = { event_id: string; label: string; date?: string | null; region?: string | null; event_type?: string | null; participants: number; metadata: DashboardDetailRow[]; personal_rows: DashboardDetailRow[]; medical_rows: DashboardDetailRow[]; emergency_rows: DashboardDetailRow[] };

export function MLDashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const region = searchParams.get("region") ?? "Global";
  const startDate = searchParams.get("start_date") ?? "";
  const endDate = searchParams.get("end_date") ?? "";
  const selectedEventId = searchParams.get("event_id") ?? "";

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (region) params.set("region", region);
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    return params.toString();
  }, [endDate, region, startDate]);

  const { data: filters } = useQuery({ queryKey: ["dashboard", "filters"], queryFn: () => fetchJson<DashboardFilterOptions>("/dashboard/filters") });
  const { data, isLoading, error } = useQuery({ queryKey: ["dashboard", "ml", region, startDate, endDate], queryFn: () => fetchJson<DashboardPayload>(queryString ? `/dashboard/ml?${queryString}` : "/dashboard/ml") });
  const { data: details, isLoading: detailLoading, error: detailError } = useQuery({ queryKey: ["dashboard", "ml", "details", region, startDate, endDate], queryFn: () => fetchJson<DashboardDetailPayload>(queryString ? `/dashboard/ml/details?${queryString}` : "/dashboard/ml/details") });

  useEffect(() => {
    if (!details?.rows?.length || selectedEventId) return;
    const next = new URLSearchParams(searchParams);
    next.set("event_id", details.rows[0].id);
    setSearchParams(next, { replace: true });
  }, [details?.rows, searchParams, selectedEventId, setSearchParams]);

  const effectiveEventId = selectedEventId || details?.rows?.[0]?.id || "";
  const { data: eventDetail } = useQuery({
    queryKey: ["dashboard", "ml", "event", effectiveEventId, region, startDate, endDate],
    queryFn: () => fetchJson<MLEventDetailPayload>(`/dashboard/ml/events/${encodeURIComponent(effectiveEventId)}?region=${encodeURIComponent(region)}${startDate ? `&start_date=${startDate}` : ""}${endDate ? `&end_date=${endDate}` : ""}`),
    enabled: Boolean(effectiveEventId)
  });

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value); else next.delete(key);
    setSearchParams(next);
  }

  return (
    <section className="page">
      <div className="page-layout">
        <aside className="control-rail">
          <section className="control-panel">
            <span className="badge">Filters</span>
            <label className="field-label"><span>Region</span><select value={region} onChange={(event) => updateParam("region", event.target.value)}>{(filters?.regions ?? ["Global"]).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
            <label className="field-label"><span>Start Date</span><input type="date" value={startDate} onChange={(event) => updateParam("start_date", event.target.value)} /></label>
            <label className="field-label"><span>End Date</span><input type="date" value={endDate} onChange={(event) => updateParam("end_date", event.target.value)} /></label>
            {(details?.rows ?? []).length ? <label className="field-label"><span>Selected Event</span><select value={effectiveEventId} onChange={(event) => updateParam("event_id", event.target.value)}>{(details?.rows ?? []).map((row) => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label> : null}
          </section>
          {data ? (
            <section className="control-panel">
              <span className="badge">Current View</span>
              <div className="sidebar-meta-list">
                <div className="sidebar-meta-row"><span>Region</span><strong>{data.region}</strong></div>
                <div className="sidebar-meta-row"><span>Timeframe</span><strong>{data.timeframe}</strong></div>
                <div className="sidebar-meta-row"><span>Source</span><strong>{data.source}</strong></div>
              </div>
            </section>
          ) : null}
        </aside>

        <div className="content-stack">
          <section className="hero-card">
            <span className="badge">Mountain Leader</span>
            <h1>{data?.title ?? "ML Dashboard"}</h1>
            <p>Mountain leader activity and attendee summary with event drill-down kept in a data-first layout.</p>
          </section>

          {isLoading ? <p className="status-panel">Loading ML dashboard...</p> : null}
          {error instanceof Error ? <p className="status-panel status-error">{error.message}</p> : null}

          <section className="metric-grid">
            {(data?.metrics ?? []).map((metric) => <article key={metric.label} className="metric-card"><span className="metric-label">{metric.label}</span><strong className="metric-value">{metric.value}</strong></article>)}
          </section>

          {(data?.sections ?? []).map((section) => (
            <section key={section.title} className="section-card">
              <div className="section-header"><span className="badge">{section.title}</span></div>
              <div className="metric-grid">
                {section.metrics.map((metric) => <article key={`${section.title}-${metric.label}`} className="metric-card"><span className="metric-label">{metric.label}</span><strong className="metric-value">{metric.value}</strong></article>)}
              </div>
            </section>
          ))}

          <section className="section-card">
            <span className="badge">Event Detail</span>
            {detailLoading ? <p className="status-panel">Loading event rows...</p> : null}
            {detailError instanceof Error ? <p className="status-panel status-error">{detailError.message}</p> : null}
            <div className="table-card">
              <table className="data-table">
                <thead><tr><th>Event</th><th>Date</th><th>Region</th><th>Participants</th><th>Metadata</th></tr></thead>
                <tbody>{(details?.rows ?? []).map((row) => <tr key={row.id}><td>{row.label}</td><td>{row.date ?? ""}</td><td>{row.region ?? ""}</td><td>{row.value ?? ""}</td><td>{Object.entries(row.metadata).map(([key, value]) => `${key}: ${value}`).join(" | ")}</td></tr>)}</tbody>
              </table>
            </div>
          </section>

          {eventDetail ? (
            <>
              <section className="section-card"><span className="badge">Selected Event</span><div className="table-card"><table className="data-table"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>{eventDetail.metadata.map((row) => <tr key={row.id}><td>{row.label}</td><td>{row.value ?? ""}</td></tr>)}</tbody></table></div></section>
              <section className="section-card"><span className="badge">Personal Information</span><div className="table-card"><table className="data-table"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>{eventDetail.personal_rows.map((row) => <tr key={row.id}><td>{row.label}</td><td>{row.value ?? ""}</td></tr>)}</tbody></table></div></section>
              <section className="section-card"><span className="badge">Medical Information</span><div className="table-card"><table className="data-table"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>{eventDetail.medical_rows.map((row) => <tr key={row.id}><td>{row.label}</td><td>{row.value ?? ""}</td></tr>)}</tbody></table></div></section>
              <section className="section-card"><span className="badge">Emergency Contact Details</span><div className="table-card"><table className="data-table"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>{eventDetail.emergency_rows.map((row) => <tr key={row.id}><td>{row.label}</td><td>{row.value ?? ""}</td></tr>)}</tbody></table></div></section>
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}
