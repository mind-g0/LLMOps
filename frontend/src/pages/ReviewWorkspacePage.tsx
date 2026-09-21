import { useEffect, useState } from "react";
import { CvSidebar } from "@/components/CvSidebar";
import { CvDetail } from "@/components/CvDetail";
import { HumanReviewActions } from "@/components/HumanReviewActions";
import { LoadingState, ErrorState, EmptyState } from "@/components/LoadingState";
import { ToastStack } from "@/components/ToastStack";
import { useToast } from "@/hooks/useToast";
import { listCVReviews, updateCVReview } from "@/api/cvReviews";
import { ApiError } from "@/api/client";
import type { CVReview } from "@/types/cvReview";

export function ReviewWorkspacePage() {
  const { toasts, showToast, dismissToast } = useToast();

  const [reviews, setReviews] = useState<CVReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [usingCompatibilityShim, setUsingCompatibilityShim] = useState(false);

  async function load(signal?: AbortSignal) {
    setLoading(true);
    setError(null);
    try {
      const response = await listCVReviews({ page: 1, page_size: 200 }, signal);
      setReviews(response.items);
      setUsingCompatibilityShim(response.fromCompatibilityShim);
      setSelectedId((current) => current ?? response.items[0]?.id ?? null);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof ApiError ? err.message : "Couldn't load CV reviews.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, []);

  const selected = reviews.find((r) => r.id === selectedId) ?? null;

  async function handleDecision(status: "approved" | "not_approved", reason: string | null) {
    if (!selected) return;
    try {
      const updated = await updateCVReview(selected.id, { status, rejection_reason: reason });
      setReviews((current) => current.map((r) => (r.id === updated.id ? updated : r)));
      showToast(status === "approved" ? "CV approved." : "CV marked as not approved.");
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Couldn't update this CV.", "error");
    }
  }

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-57px)] items-center justify-center bg-[#FDFBF7]">
        <LoadingState label="Loading review workspace" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#FDFBF7] p-6 text-stone-800">
        <ErrorState description={error} onRetry={() => load()} />
      </div>
    );
  }

  return (
    <div className="relative flex h-[calc(100vh-57px)] flex-col bg-[#FDFBF7] text-stone-800">
      {/* Compatibility Shim Banner */}
      {usingCompatibilityShim && (
        <div className="flex items-center gap-2 border-b border-[#BCD9B4] bg-[#BCD9B4]/20 px-4 py-2 text-xs font-medium text-emerald-950">
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>
            Showing a compatibility view of the current API. Status details, RAG summaries, and human-review routing will appear once the backend's full CV review contract ships.
          </span>
        </div>
      )}

      <div className="grid flex-1 min-h-0 grid-cols-1 md:grid-cols-[340px_1fr]">
        {/* Left Sidebar */}
        <aside
          className={`min-h-0 border-stone-200 bg-[#F5F2EC] md:border-r ${
            selected ? "hidden md:block" : "block"
          }`}
        >
          <CvSidebar reviews={reviews} selectedId={selectedId} onSelect={setSelectedId} />
        </aside>

        {/* Right Detail Pane */}
        <section className="flex min-h-0 flex-col bg-[#FDFBF7]">
          {selected ? (
            <>
              {/* Mobile Back Button Header */}
              <div className="border-b border-stone-200 bg-[#F5F2EC] p-3 md:hidden">
                <button
                  type="button"
                  onClick={() => setSelectedId(null)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 hover:border-[#BCD9B4]"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                  </svg>
                  Back to list
                </button>
              </div>

              {/* Main CV Detail Content */}
              <div className="flex-1 overflow-y-auto bg-[#FDFBF7]">
                <CvDetail review={selected} />
              </div>

              {/* Bottom Actions Bar */}
              <div className="border-t border-stone-200 bg-white p-3 shadow-sm">
                <HumanReviewActions
                  review={selected}
                  onApprove={() => handleDecision("approved", null)}
                  onReject={(reason) => handleDecision("not_approved", reason || null)}
                />
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center bg-[#FDFBF7] p-6">
              <EmptyState
                title="No CV selected"
                description="Choose a CV from the list to see its review details."
              />
            </div>
          )}
        </section>
      </div>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}