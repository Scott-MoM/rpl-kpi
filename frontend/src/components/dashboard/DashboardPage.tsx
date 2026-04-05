import { useQuery } from "@tanstack/react-query";

import { fetchJson } from "../../lib/api";

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

type DashboardPageProps = {
  badge: string;
  endpoint: string;
  intro: string;
};

export function DashboardPage({ badge, endpoint, intro }: DashboardPageProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", endpoint],
    queryFn: () => fetchJson<DashboardPayload>(endpoint)
  });

  return (
    <section className="page">
      <section className="hero-card">
        <span className="badge">{badge}</span>
        <h1>{data?.title ?? "Dashboard"}</h1>
        <p>{intro}</p>
        {data ? (
          <div className="meta-row">
            <span className="meta-pill">Region: {data.region}</span>
            <span className="meta-pill">Timeframe: {data.timeframe}</span>
            <span className="meta-pill">Source: {data.source}</span>
          </div>
        ) : null}
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

      {(data?.sections ?? []).map((section) => (
        <section key={section.title} className="section-card">
          <div className="section-header">
            <span className="badge">{section.title}</span>
          </div>
          <div className="metric-grid">
            {section.metrics.map((metric) => (
              <article key={`${section.title}-${metric.label}`} className="metric-card">
                <span className="metric-label">{metric.label}</span>
                <strong className="metric-value">{metric.value}</strong>
                {metric.description ? <p>{metric.description}</p> : null}
              </article>
            ))}
          </div>
        </section>
      ))}

      {(data?.notes ?? []).length ? (
        <section className="section-card">
          <span className="badge">Notes</span>
          <div className="notes-list">
            {data?.notes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
