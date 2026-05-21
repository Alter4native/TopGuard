import type { CameraState, EventType, Role } from "../types";

export function canWrite(role: Role): boolean {
  return role === "admin" || role === "operator";
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function stateLabel(state: CameraState): string {
  const labels: Record<CameraState, string> = {
    online: "Online",
    offline: "Offline",
    stopped: "Stopped",
    error: "Error",
  };
  return labels[state];
}

export function eventTypeLabel(eventType: EventType): string {
  return eventType.replaceAll("_", " ");
}
