type StatusBadgeProps = {
  tone: "good" | "warn" | "danger" | "neutral";
  children: string;
};

export function StatusBadge({ tone, children }: StatusBadgeProps) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>;
}
