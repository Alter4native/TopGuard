import { FormEvent, useEffect, useState } from "react";
import { Database, Save, Settings } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import type { ModelVersion, Role, Settings as SettingsRecord } from "../types";
import { canWrite, formatDateTime } from "../utils/format";

type SettingsPageProps = {
  role: Role;
  settings: SettingsRecord | null;
  models: ModelVersion[];
  vectorStatus: unknown;
  embeddingStatus: unknown;
  onUpdate: (payload: Partial<SettingsRecord>) => Promise<void>;
};

function prettyJson(payload: unknown): string {
  return JSON.stringify(payload ?? { status: "unavailable" }, null, 2);
}

export function SettingsPage({ role, settings, models, vectorStatus, embeddingStatus, onUpdate }: SettingsPageProps) {
  const [draft, setDraft] = useState<SettingsRecord>(
    settings ?? {
      processing_fps: 5,
      person_confidence_threshold: 0.5,
      face_recognition_threshold: 0.65,
      event_cooldown_seconds: 60,
      retention_days: 30,
    },
  );
  const writable = canWrite(role);

  useEffect(() => {
    if (settings) {
      setDraft(settings);
    }
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onUpdate(draft);
  }

  return (
    <section className="page-stack">
      <div className="section-heading">
        <div>
          <h2>Settings</h2>
          <p>Manage thresholds, retention and runtime metadata for the local MVP.</p>
        </div>
      </div>

      <div className="content-grid content-grid--balanced">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h2>Thresholds</h2>
              <span>{writable ? "Editable" : "Read-only viewer access"}</span>
            </div>
            <Settings aria-hidden="true" />
          </div>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              Processing FPS
              <input
                min={1}
                max={30}
                type="number"
                value={draft.processing_fps}
                disabled={!writable}
                onChange={(event) => setDraft({ ...draft, processing_fps: Number(event.target.value) })}
              />
            </label>
            <label>
              Person confidence
              <input
                min={0}
                max={1}
                step={0.01}
                type="number"
                value={draft.person_confidence_threshold}
                disabled={!writable}
                onChange={(event) =>
                  setDraft({ ...draft, person_confidence_threshold: Number(event.target.value) })
                }
              />
            </label>
            <label>
              Face recognition threshold
              <input
                min={0}
                max={1}
                step={0.01}
                type="number"
                value={draft.face_recognition_threshold}
                disabled={!writable}
                onChange={(event) => setDraft({ ...draft, face_recognition_threshold: Number(event.target.value) })}
              />
            </label>
            <label>
              Event cooldown seconds
              <input
                min={0}
                type="number"
                value={draft.event_cooldown_seconds}
                disabled={!writable}
                onChange={(event) => setDraft({ ...draft, event_cooldown_seconds: Number(event.target.value) })}
              />
            </label>
            <label>
              Retention days
              <input
                min={1}
                type="number"
                value={draft.retention_days}
                disabled={!writable}
                onChange={(event) => setDraft({ ...draft, retention_days: Number(event.target.value) })}
              />
            </label>
            {writable ? (
              <button className="primary-button" type="submit">
                <Save aria-hidden="true" />
                Save settings
              </button>
            ) : null}
          </form>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h2>Vector database</h2>
              <span>Qdrant health and collection metadata</span>
            </div>
            <Database aria-hidden="true" />
          </div>
          <div className="status-json">
            <StatusBadge tone="neutral">AI-service vector</StatusBadge>
            <pre>{prettyJson(vectorStatus)}</pre>
            <StatusBadge tone="neutral">Backend vector</StatusBadge>
            <pre>{prettyJson(embeddingStatus)}</pre>
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <div>
            <h2>Models</h2>
            <span>{models.length} registered versions</span>
          </div>
        </div>
        {models.length ? (
          <div className="events-table" role="table" aria-label="Models">
            <div className="events-row events-head models-row" role="row">
              <span>Name</span>
              <span>Runtime</span>
              <span>Version</span>
              <span>Active</span>
              <span>Created</span>
            </div>
            {models.map((model) => (
              <div className="events-row models-row" key={model.model_id} role="row">
                <span>{model.name}</span>
                <span>{model.runtime}</span>
                <span>{model.version}</span>
                <span>{model.active ? "Yes" : "No"}</span>
                <span>{formatDateTime(model.created_at)}</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No models" body="Model registry will be updated by training/export stages." />
        )}
      </article>
    </section>
  );
}
