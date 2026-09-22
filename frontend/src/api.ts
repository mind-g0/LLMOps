declare global {
  interface Window { __RUNTIME_CONFIG__?: { VITE_API_BASE_URL?: string } }
}

const RUNTIME_URL = typeof window !== 'undefined' ? window.__RUNTIME_CONFIG__?.VITE_API_BASE_URL : undefined
const VITE_URL = typeof import.meta !== 'undefined' ? import.meta.env.VITE_API_BASE_URL : undefined
const API_BASE_URL = (RUNTIME_URL || VITE_URL || 'http://localhost:8004').replace(/\/$/, '')

export type ReviewStatus = 'approved' | 'not_approved' | 'needs_human_review'

export interface JobRequirement {
  id?: string
  name: string
  title: string
  description: string
  requirements: string[]
  active?: boolean
  created_at?: string
  updated_at?: string
}

export interface CVReview {
  id: string
  cvName: string
  approved: boolean
  status: ReviewStatus
  rejectionReason?: string
  cvObjectKey: string
  contentType: string | null
  jobRequirementId: string | null
  jobRequirement: string
  ragSummary: string
  strengths: string[]
  missingRequirements: string[]
  matchingRequirements: string[]
  match_score: number | null
  createdAt: string
  fileUrl?: string
  reportData?: Record<string, unknown>
}

export interface PaginatedReviews {
  items: CVReview[]
  page: number
  page_size: number
  total: number
}

function mapReview(review: any): CVReview {
  const snapshot = review.job_requirement_snapshot
  return {
    id: review.id,
    cvName: review.cv_name,
    approved: review.approved,
    status: review.status,
    rejectionReason: review.rejection_reason || undefined,
    cvObjectKey: review.cv_object_key,
    contentType: review.content_type,
    jobRequirementId: review.job_requirement_id,
    jobRequirement: snapshot?.title || snapshot?.name || 'Unassigned',
    ragSummary: review.rag_summary || '',
    strengths: review.strengths || [],
    missingRequirements: review.missing_requirements || [],
    matchingRequirements: [],
    match_score: review.match_score,
    createdAt: review.created_at,
    fileUrl: review.file_url,
    reportData: review.report_data,
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  listJobs: () => request<JobRequirement[]>('/api/v1/job-requirements'),
  createJob: (job: JobRequirement) => request<JobRequirement>('/api/v1/job-requirements', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(job),
  }),
  updateJob: (id: string, job: Partial<JobRequirement>) => request<JobRequirement>(`/api/v1/job-requirements/${id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(job),
  }),
  listReviews: async (params = '') => {
    const result = await request<{ items: any[]; page: number; page_size: number; total: number }>(`/api/v1/cv-reviews${params}`)
    return { items: result.items.map(mapReview), page: result.page, page_size: result.page_size, total: result.total }
  },
  getReview: async (id: string) => mapReview(await request<any>(`/api/v1/cv-reviews/${id}`)),
  updateReview: async (id: string, status: ReviewStatus, rejection_reason: string | null) => mapReview(await request<any>(`/api/v1/cv-reviews/${id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status, rejection_reason }),
  })),
  getFileUrl: async (id: string) => (await request<{ url: string }>(`/api/v1/cv-reviews/${id}/file`)).url,
  getFileContent: async (id: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/cv-reviews/${id}/file-content`)
    if (!response.ok) throw new Error('Unable to fetch CV content')
    return URL.createObjectURL(await response.blob())
  },
  uploadReview: async (file: File, jobId: string | undefined) => {
    const data = new FormData()
    data.append('cv', file)
    data.append('status', 'needs_human_review')
    if (jobId) data.append('job_requirement_id', jobId)
    const raw = await request<any>('/api/v1/cv-reviews', { method: 'POST', body: data })
    return mapReview(raw)
  },
}
