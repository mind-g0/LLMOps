import { useEffect, useMemo, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { LoadingState, ErrorState, EmptyState } from "@/components/LoadingState";
import { Pagination } from "@/components/Pagination";
import { listCVReviews, getCVFileUrl } from "@/api/cvReviews";
import { listJobRequirements } from "@/api/jobRequirements";
import { ApiError } from "@/api/client";
import type { CVReview, CVReviewListResponse, CVStatus } from "@/types/cvReview";
import type { JobRequirement } from "@/types/jobRequirement";

const PAGE_SIZE = 10;

const STATUS_FILTERS: { value: CVStatus | "all"; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "approved", label: "Approved" },
  { value: "needs_human_review", label: "Needs human review" },
  { value: "not_approved", label: "Not approved" },
];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export function AllCvsPage() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [status, setStatus] = useState<CVStatus | "all">("all");
  const [jobId, setJobId] = useState<string>("");
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const [page, setPage] = useState(1);

  const [jobRequirements, setJobRequirements] = useState<JobRequirement[]>([]);
  const [response, setResponse] = useState<CVReviewListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    listJobRequirements(controller.signal)
      .then(setJobRequirements)
      .catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, status, jobId]);

  async function load(signal?: AbortSignal) {
    setLoading(true);
    setError(null);
    try {
      const result = await listCVReviews(
        {
          status,
          job_requirement_id: jobId || undefined,
          search: debouncedSearch || undefined,
          page,
          page_size: PAGE_SIZE,
        },
        signal
      );
      setResponse(result);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof ApiError ? err.message : "Couldn't load CVs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [debouncedSearch, status, jobId, page]);

  const items = useMemo(() => {
    const base = response?.items ?? [];
    return [...base].sort((a, b) => {
      const diff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      return sort === "newest" ? diff : -diff;
    });
  }, [response, sort]);

  const jobName = (r: CVReview) => r.job_requirement_name ?? "\u2014";

  return (
    <div className="relative min-h-screen bg-[#FDFBF7] text-stone-800">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        {/* Header */}
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-stone-900">All CVs</h1>
            <p className="mt-1 text-sm text-stone-600">
              Every CV processed through the pipeline, in one place.
            </p>
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <div className="relative w-full max-w-xs">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by filename\u2026"
              className="w-full rounded-lg border border-stone-300 bg-white pl-9 pr-3 py-2 text-sm text-stone-800 placeholder:text-stone-400 focus:border-[#BCD9B4] focus:outline-none focus:ring-2 focus:ring-[#BCD9B4]/50"
            />
          </div>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as CVStatus | "all")}
            className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm text-stone-800 focus:border-[#BCD9B4] focus:outline-none focus:ring-2 focus:ring-[#BCD9B4]/50"
          >
            {STATUS_FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>

          <select
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
            className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm text-stone-800 focus:border-[#BCD9B4] focus:outline-none focus:ring-2 focus:ring-[#BCD9B4]/50"
          >
            <option value="">All job requirements</option>
            {jobRequirements.map((job) => (
              <option key={job.id} value={job.id}>
                {job.name}
              </option>
            ))}
          </select>

          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as "newest" | "oldest")}
            className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm text-stone-800 focus:border-[#BCD9B4] focus:outline-none focus:ring-2 focus:ring-[#BCD9B4]/50"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>

        {/* Main Table Container */}
        <div className="mt-5 overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
          {loading ? (
            <div className="py-12">
              <LoadingState label="Loading CVs" />
            </div>
          ) : error ? (
            <div className="py-12">
              <ErrorState description={error} onRetry={() => load()} />
            </div>
          ) : items.length === 0 ? (
            <div className="py-12">
              <EmptyState
                title="No CVs match these filters"
                description="Try a different search term or clear the filters."
              />
            </div>
          ) : (
            <>
              {/* Desktop Table View */}
              <table className="hidden w-full text-left text-sm md:table">
                <thead className="border-b border-stone-200 bg-[#F4F1EA] text-xs font-semibold uppercase tracking-wider text-stone-600">
                  <tr>
                    <th className="px-5 py-3.5">CV name</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Job requirement</th>
                    <th className="px-5 py-3.5">Summary</th>
                    <th className="px-5 py-3.5">Processed</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {items.map((review) => (
                    <tr
                      key={review.id}
                      className="transition-colors hover:bg-[#BCD9B4]/10"
                    >
                      <td className="max-w-[200px] truncate px-5 py-4 font-medium text-stone-900">
                        {review.cv_name}
                      </td>
                      <td className="px-5 py-4">
                        <StatusBadge status={review.status} />
                      </td>
                      <td className="px-5 py-4 text-stone-700">{jobName(review)}</td>
                      <td className="max-w-[240px] px-5 py-4 text-stone-500">
                        <span className="line-clamp-2 text-xs leading-relaxed">
                          {review.rejection_reason ?? review.rag_summary ?? "\u2014"}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 text-xs text-stone-400">
                        {formatDate(review.created_at)}
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 text-right">
                        <a
                          href={getCVFileUrl(review.id)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 rounded-lg border border-[#BCD9B4] bg-[#BCD9B4]/20 px-3 py-1.5 text-xs font-semibold text-emerald-950 transition-all hover:bg-[#BCD9B4]/40"
                        >
                          View CV
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Mobile Card View */}
              <ul className="divide-y divide-stone-200 md:hidden">
                {items.map((review) => (
                  <li key={review.id} className="space-y-3 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <p className="truncate text-sm font-semibold text-stone-900">{review.cv_name}</p>
                      <StatusBadge status={review.status} />
                    </div>
                    <p className="text-xs font-medium text-stone-600">{jobName(review)}</p>
                    {(review.rejection_reason || review.rag_summary) && (
                      <p className="line-clamp-2 text-xs leading-relaxed text-stone-500">
                        {review.rejection_reason ?? review.rag_summary}
                      </p>
                    )}
                    <div className="flex items-center justify-between border-t border-stone-100 pt-2 text-xs">
                      <span className="text-stone-400">{formatDate(review.created_at)}</span>
                      <a
                        href={getCVFileUrl(review.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 font-semibold text-[#415e3b] hover:underline"
                      >
                        View CV
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    </div>
                  </li>
                ))}
              </ul>

              {/* Pagination */}
              <div className="border-t border-stone-200 px-4 py-3 bg-[#FDFBF7]">
                <Pagination
                  page={response?.page ?? page}
                  pageSize={response?.page_size ?? PAGE_SIZE}
                  total={response?.total ?? items.length}
                  onPageChange={setPage}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}