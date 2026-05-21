import type { LucideIcon } from "lucide-react";

type MetricTileProps = {
  icon: LucideIcon;
  label: string;
  value: string;
  detail?: string;
};

export function MetricTile({ icon: Icon, label, value, detail }: MetricTileProps) {
  return (
    <article className="metric-tile">
      <Icon aria-hidden="true" />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {detail ? <small>{detail}</small> : null}
      </div>
    </article>
  );
}
