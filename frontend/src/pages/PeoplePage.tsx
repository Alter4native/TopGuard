import { FormEvent, useState } from "react";
import { Trash2, Upload, UserPlus } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import type { Person, PersonPayload } from "../types";
import { formatDateTime } from "../utils/format";

type PeoplePageProps = {
  persons: Person[];
  onCreate: (payload: PersonPayload) => Promise<void>;
  onUploadPhoto: (personId: string, file: File) => Promise<void>;
  onDeleteEmbeddings: (personId: string) => Promise<void>;
};

export function PeoplePage({ persons, onCreate, onUploadPhoto, onDeleteEmbeddings }: PeoplePageProps) {
  const [draft, setDraft] = useState<PersonPayload>({ display_name: "", external_id: "", notes: "" });
  const [selectedPersonId, setSelectedPersonId] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.display_name.trim()) {
      return;
    }
    await onCreate(draft);
    setDraft({ display_name: "", external_id: "", notes: "" });
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPersonId || !selectedFile) {
      return;
    }
    await onUploadPhoto(selectedPersonId, selectedFile);
    setSelectedFile(null);
  }

  return (
    <section className="page-stack">
      <div className="section-heading">
        <div>
          <h2>Known people</h2>
          <p>Manage people allowed for face recognition. Raw embeddings are never shown in the dashboard.</p>
        </div>
      </div>

      <div className="content-grid content-grid--balanced">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h2>People registry</h2>
              <span>{persons.length} profiles</span>
            </div>
          </div>
          {persons.length ? (
            <div className="person-list">
              {persons.map((person) => (
                <div className="person-row" key={person.person_id}>
                  <div className="avatar">{person.display_name.slice(0, 1).toUpperCase()}</div>
                  <div>
                    <strong>{person.display_name}</strong>
                    <span>{person.external_id ?? "No external ID"} - {person.photo_count} photos</span>
                  </div>
                  <button className="text-button danger-text" type="button" onClick={() => onDeleteEmbeddings(person.person_id)}>
                    <Trash2 aria-hidden="true" />
                    Embeddings
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No known people" body="Create a profile, upload a face photo, then register embedding metadata." />
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h2>Create person</h2>
              <span>Admin/operator only</span>
            </div>
            <UserPlus aria-hidden="true" />
          </div>
          <form className="form-grid" onSubmit={handleCreate}>
            <label>
              Display name
              <input
                value={draft.display_name}
                onChange={(event) => setDraft({ ...draft, display_name: event.target.value })}
              />
            </label>
            <label>
              External ID
              <input
                value={draft.external_id ?? ""}
                onChange={(event) => setDraft({ ...draft, external_id: event.target.value })}
              />
            </label>
            <label>
              Notes
              <textarea value={draft.notes ?? ""} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} />
            </label>
            <button className="primary-button" type="submit">
              <UserPlus aria-hidden="true" />
              Create person
            </button>
          </form>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <div>
            <h2>Upload recognition photo</h2>
            <span>Photo upload is authorized; vector profile metadata is registered after upload.</span>
          </div>
          <Upload aria-hidden="true" />
        </div>
        <form className="filter-bar" onSubmit={handleUpload}>
          <label>
            Person
            <select value={selectedPersonId} onChange={(event) => setSelectedPersonId(event.target.value)}>
              <option value="">Select person</option>
              {persons.map((person) => (
                <option key={person.person_id} value={person.person_id}>
                  {person.display_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Face photo
            <input
              type="file"
              accept="image/*"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <button className="primary-button" type="submit" disabled={!selectedPersonId || !selectedFile}>
            <Upload aria-hidden="true" />
            Upload
          </button>
        </form>
        <p className="fine-print">Last registry update is shown in person rows. Current time: {formatDateTime(new Date().toISOString())}</p>
      </article>
    </section>
  );
}
