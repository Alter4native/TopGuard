import { Activity, Camera, Gauge, Server, UserRound } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { MetricTile } from "../components/MetricTile";
import { StatusBadge } from "../components/StatusBadge";
import type { Camera as CameraRecord, EventRecord, ModelVersion, Person, Settings } from "../types";
import { eventTypeLabel, formatDateTime, formatPercent, stateLabel } from "../utils/format";

type OverviewPageProps = {
  cameras: CameraRecord[];
  events: EventRecord[];
  persons: Person[];
  models: ModelVersion[];
  settings: Settings | null;
  aiHealth: unknown;
  vectorStatus: unknown;
};

function readStatus(payload: unknown): string {
  if (payload && typeof payload === "object" && "status" in payload) {
    return String((payload as { status: unknown }).status);
  }
  return "unavailable";
}

export function OverviewPage({ cameras, events, persons, models, settings, aiHealth, vectorStatus }: OverviewPageProps) {
  const primaryCamera = cameras[0] ?? null;
  const activeModel = models.find((model) => model.active) ?? models[0] ?? null;
  const peopleCountEvent = events.find((event) => event.event_type === "people_count");
  const peopleNow = peopleCountEvent?.metadata.people_count ?? peopleCountEvent?.metadata.count ?? 0;

  return (
    <>
      <section className="status-grid" aria-label="Platform status">
        <MetricTile
          icon={Camera}
          label="Camera status"
          value={primaryCamera ? stateLabel(primaryCamera.state) : "No camera"}
          detail={primaryCamera?.name}
        />
        <MetricTile icon={UserRound} label="Known people" value={String(persons.length)} detail="Admin/operator only" />
        <MetricTile
          icon={Gauge}
          label="Processing FPS"
          value={String(settings?.processing_fps ?? primaryCamera?.processing_fps ?? 0)}
          detail="Frame sampling target"
        />
        <MetricTile icon={Activity} label="AI service" value={readStatus(aiHealth)} detail="Detector/tracker runtime" />
      </section>

      <section className="content-grid">
        <article className="panel live-panel">
          <div className="panel-header">
            <div>
              <h2>Live/status view</h2>
              <span>{primaryCamera ? primaryCamera.name : "No camera configured"}</span>
            </div>
            <StatusBadge tone={primaryCamera?.state === "online" ? "good" : "neutral"}>
              {primaryCamera ? stateLabel(primaryCamera.state) : "Stopped"}
            </StatusBadge>
          </div>
          <div className="video-frame" aria-label="Live camera placeholder">
            <div className="person-box person-box-a">
              <span>#14 person</span>
            </div>
            <div className="person-box person-box-b">
              <span>#18 unknown</span>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h2>Recognition</h2>
              <span>Threshold {settings?.face_recognition_threshold ?? 0.65}</span>
            </div>
          </div>
          <div className="recognition-list">
            <div>
              <span>People now</span>
              <strong>{String(peopleNow)}</strong>
            </div>
            <div>
              <span>Known profiles</span>
              <strong>{persons.length}</strong>
            </div>
            <div>
              <span>Vector DB</span>
              <strong>{readStatus(vectorStatus)}</strong>
            </div>
          </div>
        </article>
      </section>

      <section className="content-grid content-grid--balanced">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h2>Recent events</h2>
              <span>{events.length} loaded</span>
            </div>
          </div>
          {events.length ? (
            <div className="compact-list">
              {events.slice(0, 5).map((event) => (
                <div className="compact-row" key={event.event_id}>
                  <div>
                    <strong>{eventTypeLabel(event.event_type)}</strong>
                    <span>{formatDateTime(event.timestamp)}</span>
                  </div>
                  <span>{formatPercent(event.confidence)}</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No events yet" body="Events will appear after AI-service starts publishing detections." />
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h2>Model runtime</h2>
              <span>Active detector model</span>
            </div>
            <Server aria-hidden="true" />
          </div>
          {activeModel ? (
            <div className="definition-list">
              <div>
                <span>Name</span>
                <strong>{activeModel.name}</strong>
              </div>
              <div>
                <span>Runtime</span>
                <strong>{activeModel.runtime}</strong>
              </div>
              <div>
                <span>Version</span>
                <strong>{activeModel.version}</strong>
              </div>
            </div>
          ) : (
            <EmptyState title="No model registered" body="Stage 12 will add training and registry updates." />
          )}
        </article>
      </section>
    </>
  );
}
