import { useState } from "react";
import type { CVReview } from "@/types/cvReview";
import { ConfirmDialog } from "./ConfirmDialog";

interface HumanReviewActionsProps {
  review: CVReview;
  onApprove: () => Promise<void> | void;
  onReject: (reason: string) => Promise<void> | void;
}

export function HumanReviewActions({ review, onApprove, onReject }: HumanReviewActionsProps) {
  const [pendingAction, setPendingAction] = useState<"approve" | "reject" | null>(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (review.status !== "needs_human_review") return null;

  async function confirmApprove() {
    setSubmitting(true);
    try {
      await onApprove();
      setPendingAction(null);
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmReject() {
    setSubmitting(true);
    try {
      await onReject(reason.trim());
      setPendingAction(null);
      setReason("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border-t border-ink-100 bg-white p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-ink-500">Human review needed</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setPendingAction("approve")}
          className="focus-ring flex-1 rounded-md bg-approved px-3 py-2 text-sm font-medium text-white hover:bg-approved/90"
        >
          Approve
        </button>
        <button
          type="button"
          onClick={() => setPendingAction("reject")}
          className="focus-ring flex-1 rounded-md bg-rejected px-3 py-2 text-sm font-medium text-white hover:bg-rejected/90"
        >
          Not approved
        </button>
      </div>

      <ConfirmDialog
        open={pendingAction === "approve"}
        title="Approve this CV?"
        description={`${review.cv_name} will be marked as approved.`}
        confirmLabel={submitting ? "Approving\u2026" : "Approve"}
        confirmDisabled={submitting}
        tone="default"
        onConfirm={confirmApprove}
        onCancel={() => setPendingAction(null)}
      />

      <ConfirmDialog
        open={pendingAction === "reject"}
        title="Mark as not approved?"
        description={`${review.cv_name} will be marked as not approved.`}
        confirmLabel={submitting ? "Submitting\u2026" : "Confirm"}
        confirmDisabled={submitting}
        tone="danger"
        onConfirm={confirmReject}
        onCancel={() => {
          setPendingAction(null);
          setReason("");
        }}
      >
        <label className="block text-xs font-medium text-ink-600" htmlFor="rejection-reason">
          Reason (optional)
        </label>
        <textarea
          id="rejection-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          placeholder="Why doesn't this candidate fit the role?"
          className="focus-ring mt-1 w-full resize-none rounded-md border border-ink-200 px-3 py-1.5 text-sm placeholder:text-ink-400"
        />
      </ConfirmDialog>
    </div>
  );
}
