import { FormEvent, useMemo, useState } from "react";
import { CalendarDays, Filter, Image } from "lucide-react";

import type { EventFilters } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import type { Camera, EventRecord, EventType, SnapshotMetadata } from "../types";
import { eventTypeLabel, formatDateTime, formatPercent } from "../utils/format";

type EventsPageProps = {
  cameras: Camera[];
  events: EventRecord[];
  filters: EventFilters;
  snapshot: SnapshotMetadata | null;
  onApplyFilters: (filters: EventFilters) => Promise<void>;
  onLoadSnapshot: (eventId: string) => Promise<void>;
};

const eventTypes: EventType[] = [
  "person_detected",
  "known_person_detected",
  "unknown_person_detected",
  "restricted_zone_entry",
  "camera_offline",
  "people_count",
];

function snapshotTone(event: EventRecord) {
  return event.snapshot_url ? "good" : "neutral";
}

export function EventsPage({ cameras, events, filters, snapshot, onApplyFilters, onLoadSnapshot }: EventsPageProps) {
  const [draft, setDraft] = useState<EventFilters>(filters);
  const cameraById = useMemo(() => new Map(cameras.map((camera) => [camera.camera_id, camera.name])), [cameras]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onApplyFilters(draft);
  }

  return (
    <section className="page-stack">
      <div className="section-heading">
        <div>
          <h2>Events</h2>
          <p>Filter person detections, camera status events, restricted zone entries and people count updates.</p>
        </div>
      </div>

      <article className="panel">
        <form className="filter-bar" onSubmit={handleSubmit}>
          <label>
            Camera
            <select value={draft.cameraId ?? ""} onChange={(event) => setDraft({ ...draft, cameraId: event.target.value })}>
              <option value="">All cameras</option>
              {cameras.map((camera) => (
                <option key={camera.camera_id} value={camera.camera_id}>
                  {camera.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Event type
            <select
              value={draft.eventType ?? ""}
              onChange={(event) => setDraft({ ...draft, eventType: event.target.value as EventType | "" })}
            >
              <option value="">All events</option>
              {eventTypes.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {eventTypeLabel(eventType)}
                </option>
              ))}
            </select>
          </label>
          <label>
            From
            <input
              type="datetime-local"
              value={draft.dateFrom ?? ""}
              onChange={(event) => setDraft({ ...draft, dateFrom: event.target.value })}
            />
          </label>
          <label>
            To
            <input
              type="datetime-local"
              value={draft.dateTo ?? ""}
              onChange={(event) => setDraft({ ...draft, dateTo: event.target.value })}
            />
          </label>
          <button className="primary-button" type="submit">
            <Filter aria-hidden="true" />
            Apply
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              setDraft({});
              void onApplyFilters({});
            }}
          >
            Clear
          </button>
        </form>
      </article>

      <article className="panel events-panel">
        <div className="panel-header">
          <div>
            <h2>Event stream</h2>
            <span>{events.length} events</span>
          </div>
          <CalendarDays aria-hidden="true" />
        </div>

        {events.length ? (
          <div className="events-table" role="table" aria-label="Events">
            <div className="events-row events-head" role="row">
              <span>Time</span>
              <span>Type</span>
              <span>Camera</span>
              <span>Confidence</span>
              <span>Snapshot</span>
              <span>Action</span>
            </div>
            {events.map((event) => (
              <div className="events-row" role="row" key={event.event_id}>
                <span>{formatDateTime(event.timestamp)}</span>
                <span>{eventTypeLabel(event.event_type)}</span>
                <span>{cameraById.get(event.camera_id) ?? event.camera_id}</span>
                <span>{formatPercent(event.confidence)}</span>
                <span>
                  <StatusBadge tone={snapshotTone(event)}>{event.snapshot_url ? "Private" : "None"}</StatusBadge>
                </span>
                <span>
                  <button
                    className="text-button"
                    type="button"
                    disabled={!event.snapshot_url}
                    onClick={() => onLoadSnapshot(event.event_id)}
                  >
                    <Image aria-hidden="true" />
                    View
                  </button>
                </span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No matching events" body="Adjust filters or start AI-service to ingest detections." />
        )}
      </article>

      {snapshot ? (
        <article className="panel snapshot-panel">
          <div className="panel-header">
            <div>
              <h2>Authorized snapshot</h2>
              <span>Snapshot is resolved through API, not a public static URL.</span>
            </div>
            <StatusBadge tone="good">{snapshot.access}</StatusBadge>
          </div>
          <div className="snapshot-preview">
            <Image aria-hidden="true" />
            <div>
              <span>Storage key</span>
              <strong>{snapshot.snapshot_storage_key}</strong>
            </div>
          </div>
        </article>
      ) : null}
    </section>
  );
}
