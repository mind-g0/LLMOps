import type { CVReview } from "@/types/cvReview";
import { StatusBadge } from "./StatusBadge";
import { getCVFileUrl } from "@/api/cvReviews";

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function RequirementList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "positive" | "negative";
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">{title}</h3>
      <ul className="mt-2 space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-ink-700">
            <span
              className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${
                tone === "positive" ? "bg-approved" : "bg-rejected"
              }`}
              aria-hidden="true"
            />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CvDetail({ review }: { review: CVReview }) {
  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink-950">{review.cv_name}</h2>
          <p className="mt-1 text-sm text-ink-500">
            {review.job_requirement_name ?? "No job requirement linked"}
          </p>
        </div>
        <StatusBadge status={review.status} />
      </div>

      <dl className="grid grid-cols-2 gap-4 rounded-lg border border-ink-100 bg-white p-4 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-ink-400">Processed</dt>
          <dd className="mt-0.5 text-ink-800">{formatTimestamp(review.created_at)}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-400">Original CV</dt>
          <dd className="mt-0.5">
            <a
              href={getCVFileUrl(review.id)}
              target="_blank"
              rel="noreferrer"
              className="focus-ring rounded text-signal underline underline-offset-2"
            >
              View / download
            </a>
          </dd>
        </div>
      </dl>

      {review.rag_summary && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">RAG summary</h3>
          {/* rag_summary is model-generated and untrusted: rendered as plain
              text only, never as HTML. */}
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink-700">
            {review.rag_summary}
          </p>
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        <RequirementList title="Candidate strengths" items={review.strengths} tone="positive" />
        <RequirementList title="Matching requirements" items={review.matching_requirements} tone="positive" />
        <RequirementList title="Missing requirements" items={review.missing_requirements} tone="negative" />
      </div>

      {review.rejection_reason && (
        <div className="rounded-lg border border-rejected-border bg-rejected-bg p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-rejected">Rejection reason</h3>
          <p className="mt-1.5 text-sm text-ink-700">{review.rejection_reason}</p>
        </div>
      )}
    </div>
  );
}
