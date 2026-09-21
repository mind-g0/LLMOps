import type { CVStatus } from "@/types/cvReview";
import { STATUS_LABEL } from "@/types/cvReview";

const STYLES: Record<CVStatus, string> = {
  approved: "bg-approved-bg text-approved border-approved-border",
  not_approved: "bg-rejected-bg text-rejected border-rejected-border",
  needs_human_review: "bg-review-bg text-review border-review-border",
};

const DOT: Record<CVStatus, string> = {
  approved: "bg-approved",
  not_approved: "bg-rejected",
  needs_human_review: "bg-review",
};

export function StatusBadge({ status, className = "" }: { status: CVStatus; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${STYLES[status]} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${DOT[status]}`} aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}
