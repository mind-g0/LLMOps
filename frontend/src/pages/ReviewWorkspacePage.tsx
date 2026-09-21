import { useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import CvSidebar from '../components/CvSidebar'
import CvDetail from '../components/CvDetail'
import HumanReviewActions from '../components/HumanReviewActions'

import type { CVReview } from '../types/cvReview'

const initialReviews: CVReview[] = [
  {
    id: '1',
    cvName: 'Ahmed_CV.pdf',
    status: 'approved',
    jobRequirement: 'AI Engineer',
    ragSummary:
      'The candidate demonstrates strong experience in Python, machine learning, and AI development. The CV aligns well with the main requirements of the AI Engineer role.',
    strengths: [
      'Strong Python development experience',
      'Experience with machine learning projects',
      'Good understanding of AI technologies',
    ],
    matchingRequirements: [
      'Python',
      'Machine Learning',
      'AI Development',
    ],
    missingRequirements: [],
    createdAt: '2026-09-21',
  },

  {
    id: '2',
    cvName: 'Sara_CV.pdf',
    status: 'needs_human_review',
    jobRequirement: 'Data Engineer',
    ragSummary:
      'The candidate matches several technical requirements but some experience details require human verification before a final decision is made.',
    strengths: [
      'Good SQL knowledge',
      'Experience working with data pipelines',
      'Strong analytical background',
    ],
    matchingRequirements: [
      'SQL',
      'Data Pipelines',
      'Python',
    ],
    missingRequirements: [
      'Cloud certification is not clearly listed',
      'Required years of experience need verification',
    ],
    createdAt: '2026-09-21',
  },

  {
    id: '3',
    cvName: 'Khalid_CV.pdf',
    status: 'not_approved',
    jobRequirement: 'DevOps Engineer',
    ragSummary:
      'The candidate has general IT experience, but the CV does not demonstrate enough of the required DevOps technologies for this position.',
    strengths: [
      'General Linux knowledge',
      'Basic infrastructure experience',
    ],
    matchingRequirements: [
      'Linux',
    ],
    missingRequirements: [
      'Docker experience',
      'Kubernetes experience',
      'CI/CD experience',
    ],
    rejectionReason:
      'The CV does not demonstrate the required DevOps experience for this role.',
    createdAt: '2026-09-21',
  },

  {
    id: '4',
    cvName: 'Noura_CV.pdf',
    status: 'approved',
    jobRequirement: 'Data Engineer',
    ragSummary:
      'Strong data engineering background with relevant technical experience.',
    strengths: [
      'Strong Python experience',
      'Advanced SQL knowledge',
      'Data pipeline experience',
    ],
    matchingRequirements: [
      'Python',
      'SQL',
      'Data Pipelines',
    ],
    missingRequirements: [],
    createdAt: '2026-09-20',
  },

  {
    id: '5',
    cvName: 'Fahad_CV.pdf',
    status: 'needs_human_review',
    jobRequirement: 'AI Engineer',
    ragSummary:
      'Good AI background, but some experience details require human verification.',
    strengths: [
      'Python development',
      'AI knowledge',
      'Machine learning experience',
    ],
    matchingRequirements: [
      'Python',
      'Machine Learning',
    ],
    missingRequirements: [
      'Required years of experience need verification',
    ],
    createdAt: '2026-09-20',
  },

  {
    id: '6',
    cvName: 'Reem_CV.pdf',
    status: 'not_approved',
    jobRequirement: 'Data Engineer',
    ragSummary:
      'Candidate does not meet several required technical requirements.',
    strengths: [
      'Basic SQL knowledge',
    ],
    matchingRequirements: [
      'SQL',
    ],
    missingRequirements: [
      'Python',
      'Data Pipelines',
    ],
    rejectionReason:
      'Several required technical skills were not found.',
    createdAt: '2026-09-19',
  },
]

interface ReviewLocationState {
  selectedCvId?: string
}

function ReviewWorkspacePage() {
  const { t } = useTranslation()
  const location = useLocation()

  const locationState =
    location.state as ReviewLocationState | null

  const requestedCvId = locationState?.selectedCvId

  const initialSelectedId =
    requestedCvId &&
    initialReviews.some(
      (review) => review.id === requestedCvId,
    )
      ? requestedCvId
      : initialReviews.find(
          (review) =>
            review.status === 'needs_human_review',
        )?.id ?? initialReviews[0]?.id ?? null

  const [reviews, setReviews] =
    useState<CVReview[]>(initialReviews)

  const [selectedId, setSelectedId] =
    useState<string | null>(initialSelectedId)

  const selectedReview = useMemo(
    () =>
      reviews.find(
        (review) => review.id === selectedId,
      ) ?? null,
    [reviews, selectedId],
  )

  const approvedCount = reviews.filter(
    (review) => review.status === 'approved',
  ).length

  const humanReviewCount = reviews.filter(
    (review) =>
      review.status === 'needs_human_review',
  ).length

  const notApprovedCount = reviews.filter(
    (review) => review.status === 'not_approved',
  ).length

  const handleSelect = (id: string) => {
    setSelectedId(id)
  }

  const handleApprove = () => {
    if (!selectedReview) return

    setReviews((currentReviews) =>
      currentReviews.map((review) =>
        review.id === selectedReview.id
          ? {
              ...review,
              status: 'approved',
              rejectionReason: undefined,
            }
          : review,
      ),
    )
  }

  const handleReject = (reason: string) => {
    if (!selectedReview) return

    setReviews((currentReviews) =>
      currentReviews.map((review) =>
        review.id === selectedReview.id
          ? {
              ...review,
              status: 'not_approved',
              rejectionReason: reason,
            }
          : review,
      ),
    )
  }

  const handleRefresh = () => {
    setReviews(initialReviews)

    if (
      requestedCvId &&
      initialReviews.some(
        (review) => review.id === requestedCvId,
      )
    ) {
      setSelectedId(requestedCvId)
      return
    }

    setSelectedId(
      initialReviews.find(
        (review) =>
          review.status === 'needs_human_review',
      )?.id ??
        initialReviews[0]?.id ??
        null,
    )
  }

  return (
    <div className="py-6 sm:py-10">

      {/* Page Header */}
      <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">

        <div>
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-300">
            <span className="h-2 w-2 rounded-full bg-blue-500" />

            {t('review.badge')}
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-4xl">
            {t('review.title')}
          </h1>

          <p className="mt-3 max-w-3xl text-slate-600 dark:text-slate-400">
            {t('review.description')}
          </p>
        </div>

        <button
          type="button"
          onClick={handleRefresh}
          className="w-fit rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          {t('review.refresh')}
        </button>

      </div>

      {/* Summary Cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
            {t('review.totalCvs')}
          </p>

          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">
            {reviews.length}
          </p>
        </div>

        <div className="rounded-2xl border border-green-200 bg-green-50 p-5 shadow-sm dark:border-green-900 dark:bg-green-950/30">
          <p className="text-sm font-medium text-green-700 dark:text-green-300">
            {t('review.approved')}
          </p>

          <p className="mt-2 text-3xl font-bold text-green-700 dark:text-green-300">
            {approvedCount}
          </p>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
            {t('review.needsHumanReview')}
          </p>

          <p className="mt-2 text-3xl font-bold text-amber-700 dark:text-amber-300">
            {humanReviewCount}
          </p>
        </div>

        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 shadow-sm dark:border-red-900 dark:bg-red-950/30">
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            {t('review.notApproved')}
          </p>

          <p className="mt-2 text-3xl font-bold text-red-700 dark:text-red-300">
            {notApprovedCount}
          </p>
        </div>

      </div>

      {/* Review Workspace */}
      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">

        <CvSidebar
          reviews={reviews}
          selectedId={selectedId}
          onSelect={handleSelect}
        />

        <div className="min-w-0">
          <CvDetail review={selectedReview} />

          {selectedReview && (
            <HumanReviewActions
              review={selectedReview}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          )}
        </div>

      </div>

    </div>
  )
}

export default ReviewWorkspacePage