import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { CollapsibleSection } from "../components/layout/CollapsibleSection";
import { StatCard } from "../components/layout/StatCard";
import { useSession } from "../app/session";
import { fetchJson } from "../lib/api";

type CaseStudyItem = { id?: string | null; title: string; content: string; region: string; date_added: string };
type DashboardFilterOptions = { regions: string[] };

const caseStudyRegions = ["Global", "North of England", "South of England", "Midlands", "Wales", "Other"];

export function CaseStudiesPage() {
  const { user } = useSession();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [region, setRegion] = useState("Global");
  const [dateAdded, setDateAdded] = useState(new Date().toISOString().slice(0, 10));
  const [selectedStudy, setSelectedStudy] = useState<CaseStudyItem | null>(null);
  const viewRegion = searchParams.get("region") ?? (user?.roles.some((role) => ["Admin", "Manager", "RPL", "ML"].includes(role)) ? "Global" : user?.region ?? "Global");

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (viewRegion && viewRegion !== "Global") params.set("region", viewRegion);
    return params.toString();
  }, [viewRegion]);

  const { data: filters } = useQuery({ queryKey: ["dashboard", "filters"], queryFn: () => fetchJson<DashboardFilterOptions>("/dashboard/filters") });
  const { data, isLoading, error } = useQuery({ queryKey: ["case-studies", viewRegion], queryFn: () => fetchJson<CaseStudyItem[]>(`/case-studies${queryString ? `?${queryString}` : ""}`) });

  const createCaseStudy = useMutation({
    mutationFn: (payload: CaseStudyItem) => fetchJson<CaseStudyItem>("/case-studies", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      setTitle("");
      setContent("");
      queryClient.invalidateQueries({ queryKey: ["case-studies"] });
    }
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createCaseStudy.mutate({ title, content, region, date_added: `${dateAdded} 00:00:00` });
  }

  function updateViewRegion(nextRegion: string) {
    const next = new URLSearchParams(searchParams);
    if (nextRegion && nextRegion !== "Global") next.set("region", nextRegion); else next.delete("region");
    setSearchParams(next);
  }

  const visibleRegions = Array.from(new Set([...caseStudyRegions, ...(filters?.regions ?? [])])).sort((left, right) => {
    if (left === "Global") return -1;
    if (right === "Global") return 1;
    return left.localeCompare(right);
  });
  const caseStudies = data ?? [];
  const latestStudy = caseStudies[0];
  const uploadState = createCaseStudy.isSuccess ? "Saved" : "Ready";

  return (
    <section className="page">
      <div className="page-layout">
        <aside className="control-rail">
          <section className="control-panel">
            <span className="badge">Case Studies Region</span>
            <label className="field-label"><span>Region</span><select value={viewRegion} onChange={(event) => updateViewRegion(event.target.value)}>{visibleRegions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          </section>
          <section className="control-panel">
            <span className="badge">Upload New Case Study</span>
            <form className="stack-form" onSubmit={handleSubmit}>
              <label className="field-label"><span>Title</span><input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
              <label className="field-label"><span>Region</span><select value={region} onChange={(event) => setRegion(event.target.value)} required>{visibleRegions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label className="field-label"><span>Date</span><input type="date" value={dateAdded} onChange={(event) => setDateAdded(event.target.value)} required /></label>
              <label className="field-label"><span>Content</span><textarea value={content} onChange={(event) => setContent(event.target.value)} rows={6} required /></label>
              <button className="primary-button" type="submit" disabled={createCaseStudy.isPending}>{createCaseStudy.isPending ? "Saving..." : "Save case study"}</button>
            </form>
            {createCaseStudy.error instanceof Error ? <p className="status-panel status-error">{createCaseStudy.error.message}</p> : null}
          </section>
        </aside>

        <div className="content-stack">
          <section className="hero-card">
            <span className="badge">Case Studies</span>
            <h1>Case studies</h1>
            <p>Browse by region, then open each case study in a dedicated popup card when you want the full story.</p>
          </section>

          {isLoading ? <p className="status-panel">Loading case studies...</p> : null}
          {error instanceof Error ? <p className="status-panel status-error">{error.message}</p> : null}
          {(data?.length ?? 0) === 0 && !isLoading && !error ? <p className="status-panel">No case studies found.</p> : null}

          <section className="metric-grid">
            <StatCard label="Visible Studies" value={caseStudies.length} detail="Case studies currently available for the selected region." tone="rose" />
            <StatCard label="Viewing Region" value={viewRegion} detail="Region filter applied to the current library view." tone="blue" />
            <StatCard label="Latest Upload" value={latestStudy?.date_added ?? "None yet"} detail={latestStudy ? latestStudy.title : "Upload a new case study from the left-hand panel."} tone="mint" />
            <StatCard label="Upload Status" value={uploadState} detail={createCaseStudy.isPending ? "Saving your new case study now." : "Submission form is ready."} tone="amber" />
          </section>

          <section className="stack-list">
            {caseStudies.map((study) => (
              <CollapsibleSection
                key={study.id ?? `${study.title}-${study.date_added}`}
                badge={study.region}
                title={study.title}
                note={`Added on ${study.date_added}. Open the popup to read the full case study in a cleaner layout.`}
              >
                <div className="metric-grid">
                  <StatCard label="Region" value={study.region} detail="Geographic scope attached to this case study." tone="blue" />
                  <StatCard label="Added" value={study.date_added} detail="Date recorded for this submission." tone="amber" />
                </div>
                <p className="collapsible-note">{study.content.slice(0, 220)}{study.content.length > 220 ? "..." : ""}</p>
                <div className="meta-row">
                  <button className="primary-button" type="button" onClick={() => setSelectedStudy(study)}>Open Case Study</button>
                </div>
              </CollapsibleSection>
            ))}
          </section>
        </div>
      </div>

      {selectedStudy ? (
        <div className="modal-backdrop" role="presentation" onClick={() => setSelectedStudy(null)}>
          <div className="modal-card modal-card-wide" role="dialog" aria-modal="true" aria-label="Case study detail" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <span className="badge">Case Study</span>
                <h2 className="card-title">{selectedStudy.title}</h2>
              </div>
              <button className="secondary-button" type="button" onClick={() => setSelectedStudy(null)}>Close</button>
            </div>
            <div className="audit-detail-grid">
              <div className="audit-detail-block"><span className="metric-label">Region</span><strong>{selectedStudy.region}</strong></div>
              <div className="audit-detail-block"><span className="metric-label">Added</span><strong>{selectedStudy.date_added}</strong></div>
            </div>
            <article className="section-card case-study-popup-card">
              {selectedStudy.content.split(/\n+/).filter(Boolean).map((paragraph, index) => (
                <p key={`${selectedStudy.title}-${index}`}>{paragraph}</p>
              ))}
            </article>
          </div>
        </div>
      ) : null}
    </section>
  );
}
