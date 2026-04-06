type StatCardProps = {
  label: string;
  value: string | number;
  detail?: string | null;
  tone?: "rose" | "blue" | "amber" | "mint";
};

export function StatCard({ label, value, detail, tone = "blue" }: StatCardProps) {
  return (
    <article className={`metric-card stat-card stat-card-${tone}`}>
      <p className="stat-card-line">
        <span className="stat-card-label">{label}:</span>
        <strong className="stat-card-value">{value}</strong>
      </p>
      {detail ? <p className="stat-card-detail">{detail}</p> : null}
    </article>
  );
}
