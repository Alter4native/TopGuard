import type { CameraState, EventType, Role } from "../types";

export function canWrite(role: Role): boolean {
  return role === "admin" || role === "operator";
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return "Нет данных";
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
    online: "Онлайн",
    offline: "Офлайн",
    stopped: "Остановлена",
    error: "Ошибка",
  };
  return labels[state];
}

export function eventTypeLabel(eventType: EventType): string {
  const labels: Record<EventType, string> = {
    person_detected: "Обнаружен человек",
    known_person_detected: "Известный человек",
    unknown_person_detected: "Неизвестный человек",
    restricted_zone_entry: "Вход в запретную зону",
    camera_offline: "Камера офлайн",
    people_count: "Подсчет людей",
  };
  return labels[eventType];
}
