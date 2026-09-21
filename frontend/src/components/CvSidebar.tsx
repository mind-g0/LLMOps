import type { CVReview, CVStatus } from "@/types/cvReview";
import { STATUS_LABEL } from "@/types/cvReview";
import { StatusBadge } from "./StatusBadge";
import { EmptyState } from "./LoadingState";

const GROUP_ORDER: CVStatus[] = ["needs_human_review", "approved", "not_approved"];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

export function CvSidebar({
  reviews,
  selectedId,
  onSelect,
}: {
  reviews: CVReview[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (reviews.length === 0) {
    return (
      <div className="p-4">
        <EmptyState
          title="No processed CVs yet"
          description="Start a review from the setup page to see results here."
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {GROUP_ORDER.map((status) => {
        const group = reviews.filter((r) => r.status === status);
        if (group.length === 0) return null;
        return (
          <div key={status} className="border-b border-ink-100">
            <div className="sticky top-0 flex items-center justify-between bg-ink-50 px-4 py-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                {STATUS_LABEL[status]}
              </p>
              <span className="text-xs text-ink-400">{group.length}</span>
            </div>
            <ul>
              {group.map((review) => {
                const selected = review.id === selectedId;
                return (
                  <li key={review.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(review.id)}
                      aria-current={selected}
                      className={`focus-ring block w-full border-l-2 px-4 py-3 text-left transition-colors ${
                        selected
                          ? "border-l-signal bg-signal-light/60"
                          : "border-l-transparent hover:bg-ink-50"
                      }`}
                    >
                      <p className="truncate text-sm font-medium text-ink-900">{review.cv_name}</p>
                      <p className="mt-0.5 truncate text-xs text-ink-500">
                        {review.job_requirement_name ?? "No job requirement linked"}
                      </p>
                      <div className="mt-2 flex items-center justify-between">
                        <StatusBadge status={review.status} />
                        <span className="text-xs text-ink-400">{formatDate(review.created_at)}</span>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
