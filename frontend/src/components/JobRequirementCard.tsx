import { useEffect, useState } from "react";
import type { JobRequirement } from "@/types/jobRequirement";

interface JobRequirementCardProps {
  slotLabel: string;
  value: JobRequirement;
  onSave: (value: JobRequirement) => Promise<void> | void;
  saving?: boolean;
}

function RequirementsEditor({
  requirements,
  onChange,
}: {
  requirements: string[];
  onChange: (next: string[]) => void;
}) {
  const [draft, setDraft] = useState("");

  function add() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    onChange([...requirements, trimmed]);
    setDraft("");
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {requirements.map((req, i) => (
          <span
            key={`${req}-${i}`}
            className="inline-flex items-center gap-1 rounded-full bg-ink-100 px-2.5 py-1 text-xs text-ink-700"
          >
            {req}
            <button
              type="button"
              className="focus-ring rounded-full text-ink-400 hover:text-rejected"
              aria-label={`Remove ${req}`}
              onClick={() => onChange(requirements.filter((_, idx) => idx !== i))}
            >
              &times;
            </button>
          </span>
        ))}
        {requirements.length === 0 && (
          <span className="text-xs text-ink-400">No requirements added yet.</span>
        )}
      </div>
      <div className="mt-2 flex gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder="e.g. 5+ years in backend engineering"
          className="focus-ring flex-1 rounded-md border border-ink-200 px-3 py-1.5 text-sm placeholder:text-ink-400"
        />
        <button
          type="button"
          onClick={add}
          className="focus-ring shrink-0 rounded-md border border-ink-200 px-3 py-1.5 text-sm font-medium text-ink-700 hover:bg-ink-50"
        >
          Add
        </button>
      </div>
    </div>
  );
}

export function JobRequirementCard({ slotLabel, value, onSave, saving }: JobRequirementCardProps) {
  const [editing, setEditing] = useState(!value.name && !value.title);
  const [draft, setDraft] = useState<JobRequirement>(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  const isComplete = Boolean(draft.name.trim() && draft.title.trim());

  async function handleSave() {
    await onSave(draft);
    setEditing(false);
  }

  function handleCancel() {
    setDraft(value);
    setEditing(false);
  }

  return (
    <div className="rounded-lg border border-ink-200 bg-white shadow-panel">
      <div className="flex items-center justify-between border-b border-ink-100 px-4 py-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-400">{slotLabel}</p>
          <p className="text-sm font-medium text-ink-900">
            {value.name || (editing ? "New role" : "Not defined yet")}
          </p>
        </div>
        {!editing && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="focus-ring rounded-md px-2.5 py-1.5 text-sm font-medium text-signal hover:bg-signal-light"
          >
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div className="space-y-3 p-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600" htmlFor={`${slotLabel}-name`}>
              Job name
            </label>
            <input
              id={`${slotLabel}-name`}
              type="text"
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              placeholder="Senior Backend Engineer"
              className="focus-ring w-full rounded-md border border-ink-200 px-3 py-1.5 text-sm placeholder:text-ink-400"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600" htmlFor={`${slotLabel}-title`}>
              Job title
            </label>
            <input
              id={`${slotLabel}-title`}
              type="text"
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
              placeholder="Engineering &mdash; Platform team"
              className="focus-ring w-full rounded-md border border-ink-200 px-3 py-1.5 text-sm placeholder:text-ink-400"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600" htmlFor={`${slotLabel}-description`}>
              Description
            </label>
            <textarea
              id={`${slotLabel}-description`}
              value={draft.description}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              rows={3}
              placeholder="What this person will own, and why the role exists."
              className="focus-ring w-full resize-none rounded-md border border-ink-200 px-3 py-1.5 text-sm placeholder:text-ink-400"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600">
              Skills, experience &amp; education requirements
            </label>
            <RequirementsEditor
              requirements={draft.requirements}
              onChange={(next) => setDraft({ ...draft, requirements: next })}
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={handleCancel}
              className="focus-ring rounded-md px-3 py-1.5 text-sm font-medium text-ink-600 hover:bg-ink-100"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={!isComplete || saving}
              className="focus-ring rounded-md bg-signal px-3 py-1.5 text-sm font-medium text-white hover:bg-signal-dark disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Saving\u2026" : "Save"}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-2 p-4">
          <p className="text-xs text-ink-500">{value.title || "No title yet"}</p>
          {value.description && (
            <p className="line-clamp-3 text-sm text-ink-700">{value.description}</p>
          )}
          {value.requirements.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {value.requirements.map((req, i) => (
                <span
                  key={`${req}-${i}`}
                  className="rounded-full bg-ink-100 px-2.5 py-1 text-xs text-ink-700"
                >
                  {req}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
