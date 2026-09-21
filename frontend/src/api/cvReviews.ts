import { apiClient } from "./client";
import type {
  CVReview,
  CVReviewListParams,
  CVReviewListResponse,
  CVStatus,
  LegacyCVReview,
} from "@/types/cvReview";
import { mapLegacyCVReview } from "@/types/cvReview";

const BASE = "/api/v1/cv-reviews";

/**
 * True once the backend ships the routes listed as "required before full
 * integration" in the frontend brief (analyze, filtered list, patch,
 * file). Flip this to `false` if those routes are not live yet -- the app
 * falls back to the current legacy endpoints and maps their shape
 * client-side, while surfacing that it's doing so (see
 * `CVReviewListResponse.fromCompatibilityShim`).
 */
export const BACKEND_HAS_FULL_CONTRACT = false;

export interface StartAnalysisPayload {
  files: File[];
  jobRequirementId: string;
}

export function startAnalysis(
  { files, jobRequirementId }: StartAnalysisPayload,
  signal?: AbortSignal
): Promise<{ id?: string } | CVReview[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("cv", file));
  formData.append("job_requirement_id", jobRequirementId);
  return apiClient.postForm(`${BASE}/analyze`, formData, signal);
}

async function listLegacy(signal?: AbortSignal): Promise<LegacyCVReview[]> {
  return apiClient.get<LegacyCVReview[]>(BASE, undefined, signal);
}

function applyClientSideFilters(
  items: CVReview[],
  params: CVReviewListParams
): CVReview[] {
  let result = items;
  if (params.status && params.status !== "all") {
    result = result.filter((item) => item.status === params.status);
  }
  if (params.job_requirement_id) {
    result = result.filter((item) => item.job_requirement_id === params.job_requirement_id);
  }
  if (params.search) {
    const search = params.search.toLowerCase();
    result = result.filter((item) => item.cv_name.toLowerCase().includes(search));
  }
  result = [...result].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
  return result;
}

export async function listCVReviews(
  params: CVReviewListParams = {},
  signal?: AbortSignal
): Promise<CVReviewListResponse> {
  const page = params.page ?? 1;
  const pageSize = params.page_size ?? 20;

  if (BACKEND_HAS_FULL_CONTRACT) {
    return apiClient.get<CVReviewListResponse>(
      BASE,
      {
        status: params.status,
        job_requirement_id: params.job_requirement_id,
        search: params.search,
        page,
        page_size: pageSize,
      },
      signal
    );
  }

  const legacy = await listLegacy(signal);
  const mapped = legacy.map(mapLegacyCVReview);
  const filtered = applyClientSideFilters(mapped, params);
  const start = (page - 1) * pageSize;
  const pageItems = filtered.slice(start, start + pageSize);

  return {
    items: pageItems,
    total: filtered.length,
    page,
    page_size: pageSize,
    fromCompatibilityShim: true,
  };
}

export async function getCVReview(id: string, signal?: AbortSignal): Promise<CVReview> {
  if (BACKEND_HAS_FULL_CONTRACT) {
    return apiClient.get<CVReview>(`${BASE}/${id}`, undefined, signal);
  }
  const legacy = await apiClient.get<LegacyCVReview>(`${BASE}/${id}`, undefined, signal);
  return mapLegacyCVReview(legacy);
}

export interface UpdateCVReviewPayload {
  status: Extract<CVStatus, "approved" | "not_approved">;
  rejection_reason: string | null;
}

export function updateCVReview(
  id: string,
  payload: UpdateCVReviewPayload,
  signal?: AbortSignal
): Promise<CVReview> {
  return apiClient.patch<CVReview>(`${BASE}/${id}`, payload, signal);
}

export function getCVFileUrl(id: string): string {
  // Resolved directly to a route rather than fetched, so it can be used as
  // an <a href> / download link. The backend is responsible for returning
  // a short-lived, credential-free URL or streaming the file itself.
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
  return `${base.replace(/\/+$/, "")}${BASE}/${id}/file`;
}
