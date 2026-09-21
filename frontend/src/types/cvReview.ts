export type CVStatus = "approved" | "not_approved" | "needs_human_review";

export interface CVReview {
  id: string;
  cv_name: string;
  status: CVStatus;
  rag_summary: string | null;
  strengths: string[];
  missing_requirements: string[];
  matching_requirements: string[];
  rejection_reason: string | null;
  job_requirement_id: string | null;
  job_requirement_name: string | null;
  cv_file_url?: string;
  created_at: string;
}

/**
 * Shape returned by the CURRENT backend (`GET /api/v1/cv-reviews`), which
 * only knows a boolean `approved` flag and has none of the RAG / job
 * requirement / three-status fields yet. See UNCOMPLETED_BACKEND.md.
 */
export interface LegacyCVReview {
  id: string;
  cv_name: string;
  approved: boolean;
  rejection_reason: string | null;
  cv_object_key: string;
  created_at: string;
}

/**
 * Maps the current, incomplete backend response onto the target CVReview
 * shape the UI is built against, so the rest of the app can be written
 * against the final contract. `needs_human_review` cannot be represented by
 * the legacy backend at all, so a legacy record is always mapped to either
 * `approved` or `not_approved` -- the UI marks these as coming from a
 * compatibility shim so the gap stays visible instead of being hidden.
 */
export function mapLegacyCVReview(legacy: LegacyCVReview): CVReview {
  return {
    id: legacy.id,
    cv_name: legacy.cv_name,
    status: legacy.approved ? "approved" : "not_approved",
    rag_summary: null,
    strengths: [],
    missing_requirements: [],
    matching_requirements: [],
    rejection_reason: legacy.rejection_reason,
    job_requirement_id: null,
    job_requirement_name: null,
    created_at: legacy.created_at,
  };
}

export const STATUS_LABEL: Record<CVStatus, string> = {
  approved: "Approved",
  not_approved: "Not approved",
  needs_human_review: "Needs human review",
};

export interface CVReviewListParams {
  status?: CVStatus | "all";
  job_requirement_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface CVReviewListResponse {
  items: CVReview[];
  total: number;
  page: number;
  page_size: number;
  /** true when this response came from the legacy list endpoint and was
   * mapped client-side rather than returned in the final shape. */
  fromCompatibilityShim: boolean;
}
