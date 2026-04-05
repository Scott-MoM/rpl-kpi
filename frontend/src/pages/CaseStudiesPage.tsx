import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

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
            <p>Submission and region-scoped browsing now follow the same control-rail pattern as the original Streamlit view.</p>
          </section>

          {isLoading ? <p className="status-panel">Loading case studies...</p> : null}
          {error instanceof Error ? <p className="status-panel status-error">{error.message}</p> : null}
          {(data?.length ?? 0) === 0 && !isLoading && !error ? <p className="status-panel">No case studies found.</p> : null}

          <section className="stack-list">
            {(data ?? []).map((study) => (
              <article key={study.id ?? `${study.title}-${study.date_added}`} className="section-card">
                <div className="meta-row"><span className="meta-pill">{study.region}</span><span className="meta-pill">{study.date_added}</span></div>
                <h2 className="card-title">{study.title}</h2>
                <p>{study.content}</p>
              </article>
            ))}
          </section>
        </div>
      </div>
    </section>
  );
}
