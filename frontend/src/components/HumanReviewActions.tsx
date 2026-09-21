import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { CVReview } from '../types/cvReview'

interface HumanReviewActionsProps {
  review: CVReview
  onApprove: () => void
  onReject: (reason: string) => void
}

function HumanReviewActions({
  review,
  onApprove,
  onReject,
}: HumanReviewActionsProps) {
  const { t } = useTranslation()

  const [showRejectForm, setShowRejectForm] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Human actions are only available for CVs
  // that require human review.
  if (review.status !== 'needs_human_review') {
    return null
  }

  const handleApprove = () => {
    const confirmed = window.confirm(
      t('review.confirmApprove', {
        cvName: review.cvName,
      }),
    )

    if (!confirmed) return

    onApprove()

    setSuccessMessage(t('review.approvedSuccessfully'))
    setShowRejectForm(false)
    setRejectionReason('')
    setError('')
  }

  const handleOpenReject = () => {
    setShowRejectForm(true)
    setSuccessMessage('')
    setError('')
  }

  const handleCancelReject = () => {
    setShowRejectForm(false)
    setRejectionReason('')
    setError('')
  }

  const handleConfirmReject = () => {
    const reason = rejectionReason.trim()

    if (!reason) {
      setError(t('review.rejectionReasonRequired'))
      return
    }

    const confirmed = window.confirm(
      t('review.confirmNotApproved', {
        cvName: review.cvName,
      }),
    )

    if (!confirmed) return

    onReject(reason)

    setSuccessMessage(t('review.markedNotApproved'))
    setShowRejectForm(false)
    setRejectionReason('')
    setError('')
  }

  return (
    <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-colors dark:border-slate-800 dark:bg-slate-900">

      {/* Header */}
      <div>
        <p className="text-sm font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
          {t('review.humanReview')}
        </p>

        <h3 className="mt-2 text-xl font-bold text-slate-900 dark:text-white">
          {t('review.finalDecision')}
        </h3>

        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-400">
          {t('review.finalDecisionDescription')}
        </p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div
          role="status"
          className="mt-5 flex items-start gap-3 rounded-xl border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-700 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300"
        >
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold dark:bg-green-900">
            ✓
          </span>

          <p>{successMessage}</p>
        </div>
      )}

      {/* Main Actions */}
      {!showRejectForm && (
        <div className="mt-6 grid gap-3 sm:grid-cols-2">

          {/* Approve */}
          <button
            type="button"
            onClick={handleApprove}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-green-600 px-5 py-3 font-semibold text-white shadow-sm transition hover:bg-green-700 focus:outline-none focus:ring-4 focus:ring-green-500/20"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="h-5 w-5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m5 12 4 4L19 6"
              />
            </svg>

            {t('review.approve')}
          </button>

          {/* Not Approved */}
          <button
            type="button"
            onClick={handleOpenReject}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-600 px-5 py-3 font-semibold text-white shadow-sm transition hover:bg-red-700 focus:outline-none focus:ring-4 focus:ring-red-500/20"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="h-5 w-5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18 18 6M6 6l12 12"
              />
            </svg>

            {t('review.notApproved')}
          </button>

        </div>
      )}

      {/* Rejection Form */}
      {showRejectForm && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50/60 p-5 dark:border-red-900 dark:bg-red-950/20">

          <label
            htmlFor="rejectionReason"
            className="block text-sm font-bold text-slate-900 dark:text-white"
          >
            {t('review.rejectionReason')}
          </label>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {t('review.rejectionReasonDescription')}
          </p>

          <textarea
            id="rejectionReason"
            value={rejectionReason}
            onChange={(event) => {
              setRejectionReason(event.target.value)
              setError('')
            }}
            rows={4}
            placeholder={t('review.rejectionReasonPlaceholder')}
            className="mt-4 w-full resize-none rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-red-500 focus:ring-4 focus:ring-red-500/10 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-500"
          />

          {/* Error */}
          {error && (
            <p
              role="alert"
              className="mt-2 text-sm font-medium text-red-600 dark:text-red-400"
            >
              {error}
            </p>
          )}

          {/* Form Actions */}
          <div className="mt-4 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">

            <button
              type="button"
              onClick={handleCancelReject}
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              {t('review.cancel')}
            </button>

            <button
              type="button"
              onClick={handleConfirmReject}
              className="rounded-xl bg-red-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-700 focus:outline-none focus:ring-4 focus:ring-red-500/20"
            >
              {t('review.confirmNotApprovedButton')}
            </button>

          </div>
        </div>
      )}

    </div>
  )
}

export default HumanReviewActions