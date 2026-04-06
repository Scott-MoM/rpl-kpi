import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { LazyPlot } from "../components/charts/LazyPlot";
import { CollapsibleSection } from "../components/layout/CollapsibleSection";
import { StatCard } from "../components/layout/StatCard";
import { fetchJson } from "../lib/api";
import { normalizeDateParam } from "../lib/dateParams";

type DashboardMetric = { label: string; value: string | number };
type DashboardSection = { title: string; metrics: DashboardMetric[] };
type DashboardPayload = { title: string; region: string; timeframe: string; source: string; metrics: DashboardMetric[]; sections: DashboardSection[] };
type DashboardFilterOptions = { regions: string[] };
type FunderDetailPayload = { funder: string; region: string; timeframe: string; metrics: DashboardMetric[]; income_series: { label: string; value: number; series?: string | null }[]; rows: { id: string; label: string; date?: string | null; value?: string | number | null; metadata: Record<string, string | number | boolean | null> }[] };

export function FunderDashboardPage() {
  const [detailsEnabled, setDetailsEnabled] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const region = searchParams.get("region") ?? "Global";
  const funder = searchParams.get("funder") ?? "All Funders";
  const startDate = searchParams.get("start_date") ?? "";
  const endDate = searchParams.get("end_date") ?? "";
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
    params.set("region", region);
    params.set("funder", funder);
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    return params.toString();
  }, [endDate, funder, region, startDate]);

  const { data: filters } = useQuery({ queryKey: ["dashboard", "filters"], queryFn: () => fetchJson<DashboardFilterOptions>("/dashboard/filters") });
  const { data, isLoading, error } = useQuery({ queryKey: ["dashboard", "funder", queryString], queryFn: () => fetchJson<DashboardPayload>(`/dashboard/funder?${queryString}`) });
  const { data: details, isLoading: detailsLoading, error: detailsError } = useQuery({
    queryKey: ["dashboard", "funder", "details", queryString],
    queryFn: () => fetchJson<FunderDetailPayload>(`/dashboard/funder/details?${queryString}`),
    enabled: detailsEnabled
  });

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value); else next.delete(key);
    setSearchParams(next);
  }

  function commitDateParam(key: "start_date" | "end_date", value: string, setDraft: (next: string) => void) {
    const normalized = normalizeDateParam(value);
    setDraft(normalized);
    updateParam(key, normalized);
  }

  const seriesNames = Array.from(new Set((details?.income_series ?? []).map((item) => item.series || "Series")));

  return (
    <section className="page">
      <div className="page-layout">
        <aside className="control-rail">
          <section className="control-panel">
            <span className="badge">Filters</span>
            <label className="field-label"><span>Region</span><select value={region} onChange={(event) => updateParam("region", event.target.value)}>{(filters?.regions ?? ["Global"]).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
            <label className="field-label"><span>Funder</span><input value={funder} onChange={(event) => updateParam("funder", event.target.value)} /></label>
            <label className="field-label"><span>Start Date</span><input type="date" value={startDateDraft} onChange={(event) => { const value = event.target.value; setStartDateDraft(value); if (!value || normalizeDateParam(value)) updateParam("start_date", normalizeDateParam(value)); }} onBlur={(event) => commitDateParam("start_date", event.target.value, setStartDateDraft)} /></label>
            <label className="field-label"><span>End Date</span><input type="date" value={endDateDraft} onChange={(event) => { const value = event.target.value; setEndDateDraft(value); if (!value || normalizeDateParam(value)) updateParam("end_date", normalizeDateParam(value)); }} onBlur={(event) => commitDateParam("end_date", event.target.value, setEndDateDraft)} /></label>
          </section>
          {data ? (
            <section className="control-panel">
              <span className="badge">Current View</span>
              <div className="sidebar-meta-list">
                <div className="sidebar-meta-row"><span>Funder</span><strong>{funder}</strong></div>
                <div className="sidebar-meta-row"><span>Region</span><strong>{data.region}</strong></div>
                <div className="sidebar-meta-row"><span>Timeframe</span><strong>{data.timeframe}</strong></div>
              </div>
            </section>
          ) : null}
        </aside>

        <div className="content-stack">
          <section className="hero-card">
            <span className="badge">Funder View</span>
            <h1>{data?.title ?? "Funder Dashboard"}</h1>
            <p>Funding performance at a glance, with charts and supporting rows tucked into collapsible cards.</p>
          </section>

          {isLoading ? <p className="status-panel">Loading funder dashboard...</p> : null}
          {error instanceof Error ? <p className="status-panel status-error">{error.message}</p> : null}

          <section className="metric-grid">
            {(data?.metrics ?? []).map((metric) => <StatCard key={metric.label} label={metric.label} value={metric.value} tone="amber" />)}
          </section>

          {(data?.sections ?? []).map((section) => (
            <CollapsibleSection key={section.title} badge={section.title} title={section.title}>
              <div className="metric-grid">
                {section.metrics.map((metric) => <StatCard key={`${section.title}-${metric.label}`} label={metric.label} value={metric.value} tone="mint" />)}
              </div>
            </CollapsibleSection>
          ))}

          <CollapsibleSection badge="Chart" title="Income trend" defaultOpen onToggle={setDetailsEnabled}>
            {detailsLoading ? <p className="status-panel">Loading funder detail...</p> : null}
            {detailsError instanceof Error ? <p className="status-panel status-error">{detailsError.message}</p> : null}
            {details ? (
              <div className="plot-card">
                <LazyPlot
                  data={seriesNames.map((series) => ({ type: "scatter", mode: "lines+markers", name: series, x: (details.income_series ?? []).filter((item) => (item.series || "Series") === series).map((item) => item.label), y: (details.income_series ?? []).filter((item) => (item.series || "Series") === series).map((item) => item.value) }))}
                  layout={{ autosize: true, paper_bgcolor: "rgba(255,255,255,0)", plot_bgcolor: "rgba(255,255,255,0)", font: { color: "#172133" }, margin: { t: 24, r: 24, b: 48, l: 48 } }}
                  style={{ width: "100%", height: "420px" }}
                  config={{ displayModeBar: false, responsive: true }}
                />
              </div>
            ) : <p className="status-panel">Open this section to load the trend data.</p>}
          </CollapsibleSection>

          <CollapsibleSection badge="Rows" title="Funding rows" note="Expand for the underlying records." onToggle={setDetailsEnabled}>
            {details ? (
              <div className="table-card">
                <table className="data-table">
                  <thead><tr><th>Item</th><th>Date</th><th>Value</th><th>Metadata</th></tr></thead>
                  <tbody>{details.rows.map((row) => <tr key={row.id}><td>{row.label}</td><td>{row.date ?? ""}</td><td>{row.value ?? ""}</td><td>{Object.entries(row.metadata).map(([key, value]) => `${key}: ${value}`).join(" | ")}</td></tr>)}</tbody>
                </table>
              </div>
            ) : <p className="status-panel">Open this section to load the underlying rows.</p>}
          </CollapsibleSection>
        </div>
      </div>
    </section>
  );
}
