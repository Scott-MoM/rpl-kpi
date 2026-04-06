import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { useSession } from "../app/session";
import { LazyPlot } from "../components/charts/LazyPlot";
import { CollapsibleSection } from "../components/layout/CollapsibleSection";
import { StatCard } from "../components/layout/StatCard";
import { fetchJson } from "../lib/api";
import { normalizeDateParam } from "../lib/dateParams";

type ReportRow = {
  dataset: string;
  record_id: string;
  date?: string | null;
  region: string;
  category: string;
  label: string;
  status: string;
  metric_value: number;
  record_count: number;
  month?: string | null;
};

type ReportAggregateRow = {
  key: string;
  value: number;
};

type ReportResponse = {
  report_type: string;
  region: string;
  timeframe: string;
  dataset: string[];
  rows: ReportRow[];
  grouped_rows: ReportAggregateRow[];
  group_by: string;
  metric: string;
  aggregation: string;
  summary: {
    row_count: number;
    dataset_count: number;
    total_metric_value: number;
  };
  available_group_by: string[];
};

type SavedReport = {
  report_id: string;
  name: string;
  owner_email: string;
  shared_with: string[];
  config: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
};

type DashboardFilterOptions = {
  regions: string[];
};

const datasetOptions = ["People", "Organisations", "Events", "Payments", "Grants"] as const;
const outputOptions = ["Tabular", "Bar", "Pie", "Line", "Comparison", "UK Map"] as const;

export function ReportsPage() {
  const { user } = useSession();
  const queryClient = useQueryClient();
  const [shareEdits, setShareEdits] = useState<Record<string, string>>({});
  const [reportName, setReportName] = useState("Untitled Report");
  const [searchParams, setSearchParams] = useSearchParams();
  const region = searchParams.get("region") ?? "Global";
  const startDate = searchParams.get("start_date") ?? "";
  const endDate = searchParams.get("end_date") ?? "";
  const [startDateDraft, setStartDateDraft] = useState(startDate);
  const [endDateDraft, setEndDateDraft] = useState(endDate);
  const outputType = searchParams.get("output_type") ?? "Tabular";
  const datasets = searchParams.getAll("dataset");
  const groupBy = searchParams.get("group_by") ?? "region";
  const aggregation = searchParams.get("aggregation") ?? "sum";
  const metric = searchParams.get("metric") ?? "metric_value";
  const requireDate = searchParams.get("require_date") === "true";
  const minValue = searchParams.get("min_value") ?? "";
  const maxValue = searchParams.get("max_value") ?? "";
  const categoryFilters = searchParams.getAll("category_filter");
  const statusFilters = searchParams.getAll("status_filter");
  const lineInterval = searchParams.get("line_interval") ?? "Monthly";
  const compareBase = searchParams.get("compare_base") ?? "";
  const compareAlt = searchParams.get("compare_alt") ?? "";
  const rowLimit = Number(searchParams.get("row_limit") ?? "500");

  useEffect(() => {
    setStartDateDraft(startDate);
  }, [startDate]);

  useEffect(() => {
    setEndDateDraft(endDate);
  }, [endDate]);

  const selectedDatasets = datasets.length ? datasets : ["Events", "Payments"];

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    selectedDatasets.forEach((dataset) => params.append("dataset", dataset));
    categoryFilters.forEach((value) => params.append("category_filter", value));
    statusFilters.forEach((value) => params.append("status_filter", value));
    params.set("region", region);
    params.set("timeframe", `${startDate || "All time"} to ${endDate || "Now"}`);
    params.set("group_by", groupBy);
    params.set("aggregation", aggregation);
    params.set("metric", metric);
    params.set("require_date", String(requireDate));
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (minValue) params.set("min_value", minValue);
    if (maxValue) params.set("max_value", maxValue);
    return params.toString();
  }, [aggregation, categoryFilters, endDate, groupBy, maxValue, metric, minValue, region, requireDate, selectedDatasets, startDate, statusFilters]);

  const { data: filters } = useQuery({
    queryKey: ["dashboard", "filters"],
    queryFn: () => fetchJson<DashboardFilterOptions>("/dashboard/filters")
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", queryString],
    queryFn: () => fetchJson<ReportResponse>(`/reports/custom?${queryString}`)
  });

  const { data: savedReports } = useQuery({
    queryKey: ["reports", "saved", user?.email],
    queryFn: () => fetchJson<SavedReport[]>(`/reports/saved?user_email=${encodeURIComponent(user?.email ?? "")}`),
    enabled: Boolean(user?.email)
  });

  const saveReport = useMutation({
    mutationFn: () =>
      fetchJson<SavedReport>("/reports/saved", {
        method: "POST",
        body: JSON.stringify({
          report_name: reportName,
          owner_email: user?.email ?? "",
          shared_with: [],
          config: {
            dataset: selectedDatasets,
            region,
            start_date: startDate,
            end_date: endDate,
            output_type: outputType,
            group_by: groupBy,
            aggregation,
            metric,
            require_date: requireDate,
            min_value: minValue,
            max_value: maxValue,
            category_filter: categoryFilters,
            status_filter: statusFilters,
            line_interval: lineInterval,
            compare_base: compareBase,
            compare_alt: compareAlt,
            row_limit: rowLimit
          }
        })
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", "saved"] })
  });

  const updateSharing = useMutation({
    mutationFn: (report: SavedReport) =>
      fetchJson<SavedReport>("/reports/saved/share", {
        method: "POST",
        body: JSON.stringify({
          report_id: report.report_id,
          report_name: report.name,
          owner_email: report.owner_email,
          shared_with: (shareEdits[report.report_id] ?? report.shared_with.join(","))
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean)
        })
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", "saved"] })
  });

  function updateSingle(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  }

  function commitDateParam(key: "start_date" | "end_date", value: string, setDraft: (next: string) => void) {
    const normalized = normalizeDateParam(value);
    setDraft(normalized);
    updateSingle(key, normalized);
  }

  function updateToggle(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    const current = new Set(next.getAll(key));
    if (current.has(value)) current.delete(value);
    else current.add(value);
    next.delete(key);
    Array.from(current).forEach((item) => next.append(key, item));
    setSearchParams(next);
  }

  function updateDatasets(value: string) {
    const next = new URLSearchParams(searchParams);
    const current = new Set(next.getAll("dataset"));
    if (current.has(value)) current.delete(value);
    else current.add(value);
    next.delete("dataset");
    const finalValues = Array.from(current);
    (finalValues.length ? finalValues : ["Events"]).forEach((item) => next.append("dataset", item));
    setSearchParams(next);
  }

  function loadSavedReport(report: SavedReport) {
    const next = new URLSearchParams();
    const config = report.config ?? {};
    const configDatasets = Array.isArray(config.dataset) ? (config.dataset as string[]) : ["Events"];
    configDatasets.forEach((item) => next.append("dataset", item));
    for (const key of ["region", "start_date", "end_date", "output_type", "group_by", "aggregation", "metric", "require_date", "min_value", "max_value", "line_interval", "compare_base", "compare_alt", "row_limit"]) {
      const value = config[key];
      if (value !== undefined && value !== null && value !== "") next.set(key, String(value));
    }
    if (Array.isArray(config.category_filter)) for (const value of config.category_filter) next.append("category_filter", String(value));
    if (Array.isArray(config.status_filter)) for (const value of config.status_filter) next.append("status_filter", String(value));
    setReportName(report.name);
    setSearchParams(next);
  }

  function exportCsv() {
    if (!data?.rows?.length) return;
    const headers = ["dataset", "record_id", "date", "region", "category", "label", "status", "metric_value", "record_count", "month"];
    const csvRows = [
      headers.join(","),
      ...data.rows.map((row) =>
        headers
          .map((header) => {
            const value = String((row as unknown as Record<string, unknown>)[header] ?? "");
            return `"${value.split('"').join('""')}"`
          })
          .join(",")
      )
    ];
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${selectedDatasets.map((item) => item.toLowerCase()).join("-") || "custom"}-report.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  const categories = Array.from(new Set((data?.rows ?? []).map((row) => row.category).filter(Boolean))).sort();
  const statuses = Array.from(new Set((data?.rows ?? []).map((row) => row.status).filter(Boolean))).sort();
  const compareOptions = (data?.grouped_rows ?? []).map((row) => row.key);
  const baseCompare = compareBase || compareOptions[0] || "";
  const altCompare = compareAlt || compareOptions[1] || compareOptions[0] || "";

  const lineBuckets = useMemo(() => {
    const bucketMap = new Map<string, number>();
    for (const row of data?.rows ?? []) {
      const rawDate = row.date || row.month;
      if (!rawDate) continue;
      const date = new Date(rawDate);
      if (Number.isNaN(date.getTime())) continue;
      let label = "";
      if (lineInterval === "Daily") label = date.toISOString().slice(0, 10);
      else if (lineInterval === "Weekly") {
        const base = new Date(date);
        const day = base.getUTCDay() || 7;
        base.setUTCDate(base.getUTCDate() - day + 1);
        label = base.toISOString().slice(0, 10);
      } else label = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
      bucketMap.set(label, (bucketMap.get(label) ?? 0) + (metric === "record_count" ? row.record_count : row.metric_value));
    }
    return Array.from(bucketMap.entries()).sort(([left], [right]) => left.localeCompare(right)).map(([label, value]) => ({ label, value }));
  }, [data?.rows, lineInterval, metric]);

  const mapRows = (data?.grouped_rows ?? []).filter((row) => row.key && row.key !== "Unknown");
  const groupedLookup = new Map((data?.grouped_rows ?? []).map((row) => [row.key, row.value]));
  const comparisonDelta = baseCompare && altCompare ? (groupedLookup.get(altCompare) ?? 0) - (groupedLookup.get(baseCompare) ?? 0) : 0;

  return (
    <section className="page">
      <div className="page-layout">
        <aside className="control-rail">
          <section className="control-panel">
            <span className="badge">Report Filters</span>
            <div className="filter-grid">
              <label className="field-label"><span>Region</span><select value={region} onChange={(event) => updateSingle("region", event.target.value)}>{(filters?.regions ?? ["Global"]).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label className="field-label"><span>Start Date</span><input type="date" value={startDateDraft} onChange={(event) => { const value = event.target.value; setStartDateDraft(value); if (!value || normalizeDateParam(value)) updateSingle("start_date", normalizeDateParam(value)); }} onBlur={(event) => commitDateParam("start_date", event.target.value, setStartDateDraft)} /></label>
              <label className="field-label"><span>End Date</span><input type="date" value={endDateDraft} onChange={(event) => { const value = event.target.value; setEndDateDraft(value); if (!value || normalizeDateParam(value)) updateSingle("end_date", normalizeDateParam(value)); }} onBlur={(event) => commitDateParam("end_date", event.target.value, setEndDateDraft)} /></label>
              <label className="field-label"><span>Output Type</span><select value={outputType} onChange={(event) => updateSingle("output_type", event.target.value)}>{outputOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label className="field-label"><span>Group By</span><select value={groupBy} onChange={(event) => updateSingle("group_by", event.target.value)}>{(data?.available_group_by ?? ["region", "category", "status", "month", "label", "dataset"]).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label className="field-label"><span>Aggregation</span><select value={aggregation} onChange={(event) => updateSingle("aggregation", event.target.value)}>{["sum", "count", "mean"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label className="field-label"><span>Metric</span><select value={metric} onChange={(event) => updateSingle("metric", event.target.value)}>{["metric_value", "record_count"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label className="field-label"><span>Min Value</span><input type="number" value={minValue} onChange={(event) => updateSingle("min_value", event.target.value)} /></label>
              <label className="field-label"><span>Max Value</span><input type="number" value={maxValue} onChange={(event) => updateSingle("max_value", event.target.value)} /></label>
              <label className="field-label"><span>Row Limit</span><input type="number" min="10" max="5000" step="10" value={rowLimit} onChange={(event) => updateSingle("row_limit", event.target.value)} /></label>
              <label className="field-label field-checkbox"><span>Require Date</span><input type="checkbox" checked={requireDate} onChange={(event) => updateSingle("require_date", String(event.target.checked))} /></label>
              {outputType === "Line" ? <label className="field-label"><span>Line Interval</span><select value={lineInterval} onChange={(event) => updateSingle("line_interval", event.target.value)}>{["Daily", "Weekly", "Monthly"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label> : null}
              {outputType === "Comparison" ? (
                <>
                  <label className="field-label"><span>Baseline</span><select value={baseCompare} onChange={(event) => updateSingle("compare_base", event.target.value)}>{compareOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                  <label className="field-label"><span>Compare Against</span><select value={altCompare} onChange={(event) => updateSingle("compare_alt", event.target.value)}>{compareOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                </>
              ) : null}
            </div>
            <div className="meta-row dataset-toggle-row">
              {datasetOptions.map((item) => {
                const active = selectedDatasets.includes(item);
                return <button key={item} className={active ? "secondary-button dataset-toggle active-toggle" : "secondary-button dataset-toggle"} type="button" onClick={() => updateDatasets(item)}>{item}</button>;
              })}
            </div>
            {categories.length ? <div className="field-label"><span>Category Filter</span><div className="checkbox-grid">{categories.map((item) => <label key={item} className="checkbox-pill"><input type="checkbox" checked={categoryFilters.includes(item)} onChange={() => updateToggle("category_filter", item)} /><span>{item}</span></label>)}</div></div> : null}
            {statuses.length ? <div className="field-label"><span>Status Filter</span><div className="checkbox-grid">{statuses.map((item) => <label key={item} className="checkbox-pill"><input type="checkbox" checked={statusFilters.includes(item)} onChange={() => updateToggle("status_filter", item)} /><span>{item}</span></label>)}</div></div> : null}
          </section>

          <section className="control-panel">
            <span className="badge">Save Report</span>
            <label className="field-label"><span>Report Name</span><input value={reportName} onChange={(event) => setReportName(event.target.value)} /></label>
            <div className="meta-row">
              <button className="primary-button" type="button" onClick={() => saveReport.mutate()} disabled={saveReport.isPending || !user?.email}>{saveReport.isPending ? "Saving..." : "Save Current Report"}</button>
              <button className="secondary-button" type="button" onClick={exportCsv} disabled={!data?.rows?.length}>Export CSV</button>
            </div>
            {saveReport.error instanceof Error ? <p className="status-panel status-error">{saveReport.error.message}</p> : null}
          </section>
        </aside>

        <div className="content-stack">
          <section className="hero-card">
            <span className="badge">Custom Reports</span>
            <h1>Custom Reports Dashboard</h1>
            <p>Build reports quickly, then open only the chart, grouped output, or raw table you actually need.</p>
          </section>

          {isLoading ? <p className="status-panel">Loading report data...</p> : null}
          {error instanceof Error ? <p className="status-panel status-error">{error.message}</p> : null}

          <section className="metric-grid">
            <StatCard label="Rows" value={data?.summary.row_count ?? 0} tone="rose" />
            <StatCard label="Datasets" value={data?.summary.dataset_count ?? 0} tone="blue" />
            <StatCard label="Total Metric" value={(data?.summary.total_metric_value ?? 0).toFixed(1)} tone="amber" />
          </section>

          <CollapsibleSection badge="Saved" title="Saved reports">
            <div className="table-card">
              <table className="data-table">
                <thead><tr><th>Name</th><th>Owner</th><th>Updated</th><th>Shared With</th><th>Action</th></tr></thead>
                <tbody>
                  {(savedReports ?? []).map((report) => (
                    <tr key={report.report_id}>
                      <td>{report.name}</td>
                      <td>{report.owner_email}</td>
                      <td>{report.updated_at ?? ""}</td>
                      <td><input value={shareEdits[report.report_id] ?? report.shared_with.join(", ")} onChange={(event) => setShareEdits((current) => ({ ...current, [report.report_id]: event.target.value }))} /></td>
                      <td><div className="meta-row"><button className="secondary-button" type="button" onClick={() => loadSavedReport(report)}>Load</button><button className="secondary-button" type="button" onClick={() => updateSharing.mutate(report)}>Save Sharing</button></div></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {updateSharing.error instanceof Error ? <p className="status-panel status-error">{updateSharing.error.message}</p> : null}
          </CollapsibleSection>

          {outputType === "Bar" || outputType === "Pie" || outputType === "Line" || outputType === "Comparison" || outputType === "UK Map" ? (
            <CollapsibleSection badge="Chart" title="Visual output" defaultOpen>
              <div className="plot-card">
                <LazyPlot
                  data={
                    outputType === "Pie"
                      ? [{ type: "pie", labels: (data?.grouped_rows ?? []).map((row) => row.key), values: (data?.grouped_rows ?? []).map((row) => row.value) }]
                      : outputType === "Line"
                        ? [{ type: "scatter", mode: "lines+markers", x: lineBuckets.map((row) => row.label), y: lineBuckets.map((row) => row.value) }]
                        : outputType === "Comparison"
                          ? [{ type: "bar", x: [baseCompare, altCompare, "Delta"], y: [groupedLookup.get(baseCompare) ?? 0, groupedLookup.get(altCompare) ?? 0, comparisonDelta] }]
                          : outputType === "UK Map"
                            ? [{ type: "scattergeo", locationmode: "country names", locations: mapRows.map(() => "United Kingdom"), text: mapRows.map((row) => `${row.key}: ${row.value.toFixed(2)}`), lon: mapRows.map((_, index) => -6 + index * 0.7), lat: mapRows.map((_, index) => 50 + index * 0.6), marker: { size: mapRows.map((row) => Math.max(10, Math.min(40, row.value / 10 || 10))), color: mapRows.map((row) => row.value), colorscale: "Viridis", showscale: true }, mode: "markers+text", textposition: "top center" }]
                            : [{ type: "bar", x: (data?.grouped_rows ?? []).map((row) => row.key), y: (data?.grouped_rows ?? []).map((row) => row.value) }]
                  }
                  layout={{ autosize: true, paper_bgcolor: "rgba(255,255,255,0)", plot_bgcolor: "rgba(255,255,255,0)", font: { color: "#172133" }, margin: { t: 24, r: 24, b: 48, l: 48 } }}
                  style={{ width: "100%", height: "420px" }}
                  config={{ displayModeBar: false, responsive: true }}
                />
              </div>
              {outputType === "Comparison" ? <p>{altCompare || "Comparison"} is {(comparisonDelta >= 0 ? "+" : "") + comparisonDelta.toFixed(2)} against {baseCompare || "baseline"}.</p> : null}
            </CollapsibleSection>
          ) : null}

          <CollapsibleSection badge="Grouped" title="Grouped output">
            <div className="table-card">
              <table className="data-table">
                <thead><tr><th>{data?.group_by ?? "group"}</th><th>Value</th></tr></thead>
                <tbody>{(data?.grouped_rows ?? []).map((row) => <tr key={row.key}><td>{row.key}</td><td>{row.value.toFixed(2)}</td></tr>)}</tbody>
              </table>
            </div>
          </CollapsibleSection>

          <CollapsibleSection badge="Table" title="Tabular output" note="Expand for the raw rows.">
            <div className="table-card">
              <table className="data-table">
                <thead><tr><th>Dataset</th><th>Date</th><th>Region</th><th>Category</th><th>Label</th><th>Status</th><th>Metric</th></tr></thead>
                <tbody>
                  {(data?.rows ?? []).slice(0, rowLimit).map((row) => (
                    <tr key={`${row.dataset}-${row.record_id}`}>
                      <td>{row.dataset}</td><td>{row.date ?? ""}</td><td>{row.region}</td><td>{row.category}</td><td>{row.label}</td><td>{row.status}</td><td>{metric === "record_count" ? row.record_count : row.metric_value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CollapsibleSection>
        </div>
      </div>
    </section>
  );
}
