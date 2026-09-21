export type ReviewStatus =
  | 'approved'
  | 'needs_human_review'
  | 'not_approved'

export interface CVReview {
  id: string
  cvName: string
  status: ReviewStatus
  jobRequirement: string
  ragSummary: string
  strengths: string[]
  missingRequirements: string[]
  matchingRequirements: string[]
  rejectionReason?: string
  createdAt: string
  fileUrl?: string
}