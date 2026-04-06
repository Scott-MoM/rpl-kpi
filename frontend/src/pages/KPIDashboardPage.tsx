import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { CollapsibleSection } from "../components/layout/CollapsibleSection";
import { fetchJson } from "../lib/api";
import { normalizeDateParam } from "../lib/dateParams";

type DashboardMetric = {
  label: string;
  value: string | number;
  description?: string | null;
};

type DashboardSection = {
  title: string;
  metrics: DashboardMetric[];
};

type DashboardPayload = {
  title: string;
  region: string;
  timeframe: string;
  source: string;
  last_updated?: string | null;
  metrics: DashboardMetric[];
  sections: DashboardSection[];
  notes: string[];
};

type DashboardFilterOptions = {
  regions: string[];
};

type DashboardDetailRow = {
  id: string;
  label: string;
  date?: string | null;
  region?: string | null;
  value?: string | number | null;
  metadata: Record<string, string | number | boolean | null>;
};

type DashboardDetailPayload = {
  section: string;
  region: string;
  timeframe: string;
  rows: DashboardDetailRow[];
};

const sectionOptions = ["governance", "partnerships", "delivery", "income"] as const;

export function KPIDashboardPage() {
  const [selectedRowId, setSelectedRowId] = useState("");
  const [detailsEnabled, setDetailsEnabled] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const region = searchParams.get("region") ?? "Global";
  const startDate = searchParams.get("start_date") ?? "";
  const endDate = searchParams.get("end_date") ?? "";
  const section = (searchParams.get("section") ?? "delivery").toLowerCase();
  const [startDateDraft, setStartDateDraft] = useState(startDate);
  const [endDateDraft, setEndDateDraft] = useState(endDate);

  useEffect(() => {
    setStartDateDraft(startDate);
  }, [startDate]);

  useEffect(() => {
    setEndDateDraft(endDate);
  }, [endDate]);

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (region) params.set("region", region);
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    return params.toString();
  }, [endDate, region, startDate]);

  const dashboardPath = queryString ? `/dashboard/kpi?${queryString}` : "/dashboard/kpi";
  const detailPath = `/dashboard/kpi/details?${queryString ? `${queryString}&` : ""}section=${section}`;

  const { data: filters } = useQuery({
    queryKey: ["dashboard", "filters"],
    queryFn: () => fetchJson<DashboardFilterOptions>("/dashboard/filters")
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", "kpi", region, startDate, endDate],
    queryFn: () => fetchJson<DashboardPayload>(dashboardPath)
  });

  const { data: details, isLoading: isLoadingDetails, error: detailsError } = useQuery({
    queryKey: ["dashboard", "kpi", "details", section, region, startDate, endDate],
    queryFn: () => fetchJson<DashboardDetailPayload>(detailPath),
    enabled: detailsEnabled
  });

  const selectedRow = (details?.rows ?? []).find((row) => row.id === selectedRowId) ?? (details?.rows ?? [])[0] ?? null;

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  }

  function commitDateParam(key: "start_date" | "end_date", value: string, setDraft: (next: string) => void) {
    const normalized = normalizeDateParam(value);
    setDraft(normalized);
    updateParam(key, normalized);
  }

  return (
    <section className="page">
      <div className="page-layout">
        <aside className="control-rail">
          <section className="control-panel">
            <span className="badge">Time Filters</span>
            <label className="field-label">
              Region
              <select value={region} onChange={(event) => updateParam("region", event.target.value)}>
                {(filters?.regions ?? ["Global"]).map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Start Date
              <input
                type="date"
                value={startDateDraft}
                onChange={(event) => {
                  const value = event.target.value;
                  setStartDateDraft(value);
                  if (!value || normalizeDateParam(value)) {
                    updateParam("start_date", normalizeDateParam(value));
                  }
                }}
                onBlur={(event) => commitDateParam("start_date", event.target.value, setStartDateDraft)}
              />
            </label>
            <label className="field-label">
              End Date
              <input
                type="date"
                value={endDateDraft}
                onChange={(event) => {
                  const value = event.target.value;
                  setEndDateDraft(value);
                  if (!value || normalizeDateParam(value)) {
                    updateParam("end_date", normalizeDateParam(value));
                  }
                }}
                onBlur={(event) => commitDateParam("end_date", event.target.value, setEndDateDraft)}
              />
            </label>
          </section>

          <section className="control-panel">
            <span className="badge">Active Section</span>
            <label className="field-label">
              Detail Section
              <select value={section} onChange={(event) => updateParam("section", event.target.value)}>
                {sectionOptions.map((item) => (
                  <option key={item} value={item}>
                    {item[0].toUpperCase() + item.slice(1)}
                  </option>
                ))}
              </select>
            </label>
            {data ? (
              <div className="sidebar-meta-list">
                <div className="sidebar-meta-row">
                  <span>Region</span>
                  <strong>{data.region}</strong>
                </div>
                <div className="sidebar-meta-row">
                  <span>Timeframe</span>
                  <strong>{data.timeframe}</strong>
                </div>
                <div className="sidebar-meta-row">
                  <span>Source</span>
                  <strong>{data.source}</strong>
                </div>
              </div>
            ) : null}
          </section>
        </aside>

        <div className="content-stack">
          <section className="hero-card">
            <span className="badge">Live KPI Overview</span>
            <h1>{data?.title ?? "KPI Dashboard"}</h1>
            <p>Regional KPI summary rebuilt against the FastAPI service layer with section drill-downs and table detail.</p>
          </section>

          {isLoading ? <p className="status-panel">Loading dashboard data...</p> : null}
          {error instanceof Error ? <p className="status-panel status-error">{error.message}</p> : null}

          <section className="metric-grid">
            {(data?.metrics ?? []).map((metric) => (
              <article key={metric.label} className="metric-card">
                <span className="metric-label">{metric.label}</span>
                <strong className="metric-value">{metric.value}</strong>
                {metric.description ? <p>{metric.description}</p> : null}
              </article>
            ))}
          </section>

          {(data?.sections ?? []).map((item) => (
            <CollapsibleSection key={item.title} badge={item.title} title={item.title} defaultOpen={item.title.toLowerCase() === section}>
              <div className="metric-grid">
                {item.metrics.map((metric) => (
                  <article key={`${item.title}-${metric.label}`} className="metric-card">
                    <span className="metric-label">{metric.label}</span>
                    <strong className="metric-value">{metric.value}</strong>
                    {metric.description ? <p>{metric.description}</p> : null}
                  </article>
                ))}
              </div>
            </CollapsibleSection>
          ))}

          <CollapsibleSection badge="Detail" title="Section detail" note="Expand for row-level data and metadata." onToggle={setDetailsEnabled}>
            {isLoadingDetails ? <p className="status-panel">Loading section detail...</p> : null}
            {detailsError instanceof Error ? <p className="status-panel status-error">{detailsError.message}</p> : null}
            {(details?.rows ?? []).length ? (
              <label className="field-label">
                Select row
                <select value={selectedRow?.id ?? ""} onChange={(event) => setSelectedRowId(event.target.value)}>
                  {(details?.rows ?? []).map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <div className="table-card">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Date</th>
                    <th>Region</th>
                    <th>Value</th>
                    <th>Metadata</th>
                  </tr>
                </thead>
                <tbody>
                  {(details?.rows ?? []).map((row) => (
                    <tr key={row.id}>
                      <td>{row.label}</td>
                      <td>{row.date ?? ""}</td>
                      <td>{row.region ?? ""}</td>
                      <td>{row.value ?? ""}</td>
                      <td>
                        {Object.entries(row.metadata ?? {})
                          .filter(([, value]) => value !== null && value !== "")
                          .map(([key, value]) => `${key}: ${value}`)
                          .join(" | ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selectedRow ? (
              <div className="table-card">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Selected Item</th>
                      <th>Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr><td>Label</td><td>{selectedRow.label}</td></tr>
                    <tr><td>Date</td><td>{selectedRow.date ?? ""}</td></tr>
                    <tr><td>Region</td><td>{selectedRow.region ?? ""}</td></tr>
                    <tr><td>Value</td><td>{selectedRow.value ?? ""}</td></tr>
                    {Object.entries(selectedRow.metadata ?? {})
                      .filter(([, value]) => value !== null && value !== "")
                      .map(([key, value]) => (
                        <tr key={key}>
                          <td>{key}</td>
                          <td>{String(value)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </CollapsibleSection>

          {(data?.notes ?? []).length ? (
            <CollapsibleSection badge="Notes" title="Notes">
              <div className="notes-list">
                {data?.notes.map((note) => (
                  <p key={note}>{note}</p>
                ))}
              </div>
            </CollapsibleSection>
          ) : null}
        </div>
      </div>
    </section>
  );
}
