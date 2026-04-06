import type { ReactNode } from "react";

type CollapsibleSectionProps = {
  title: string;
  badge: string;
  defaultOpen?: boolean;
  note?: string;
  children: ReactNode;
};

export function CollapsibleSection({ title, badge, defaultOpen = false, note, children }: CollapsibleSectionProps) {
  return (
    <details className="section-card admin-collapsible collapsible-section" open={defaultOpen}>
      <summary className="admin-collapsible-summary">
        <div className="collapsible-summary-copy">
          <span className="badge">{badge}</span>
          <h2 className="card-title">{title}</h2>
          {note ? <p className="collapsible-note">{note}</p> : null}
        </div>
        <span className="admin-collapsible-arrow" aria-hidden="true">+</span>
      </summary>
      <div className="admin-collapsible-content">{children}</div>
    </details>
  );
}
