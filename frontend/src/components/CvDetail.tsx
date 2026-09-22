import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import StatusBadge from './StatusBadge'
import CvPreviewModal from './CvPreviewModal'
import { api } from '../api'
import type { CVReview } from '../types/cvReview'

interface CvDetailProps {
  review: CVReview | null
}

function CvDetail({ review }: CvDetailProps) {
  const { t } = useTranslation()
  const [fileUrl, setFileUrl] = useState('')
  const [fileUrlError, setFileUrlError] = useState(false)
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => {
    setFileUrl('')
    setFileUrlError(false)
    if (!review) return
    api.getFileUrl(review.id).then(setFileUrl).catch(() => setFileUrlError(true))
  }, [review?.id])

  if (!review) {
    return (
      <div className="relative overflow-hidden flex min-h-[500px] items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        
        {/* Background Glow Effect for Empty State */}
        <div className="absolute -top-12 start-1/2 -z-10 h-64 w-64 -translate-x-1/2 rounded-full bg-blue-500/15 blur-3xl dark:bg-blue-600/20 pointer-events-none" />

        <div>
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="h-7 w-7"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12h6M9 16h6M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13 2v7h7"
              />
            </svg>
          </div>

          <h2 className="mt-4 text-lg font-bold text-slate-900 dark:text-white">
            {t('review.selectACv')}
          </h2>

          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {t('review.selectCvDescription')}
          </p>
        </div>
      </div>
    )
  }

  return (
    <>
    <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">

      {/* Background Glow Effect */}
      <div className="absolute -top-16 start-1/2 -z-10 h-80 w-80 -translate-x-1/2 rounded-full bg-blue-500/15 blur-3xl dark:bg-blue-600/20 pointer-events-none" />

      {/* Header */}
      <div className="border-b border-slate-200 p-6 dark:border-slate-800">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

          <div className="min-w-0">
            <p className="text-sm font-semibold text-blue-600 dark:text-blue-400">
              {t('review.cvReview')}
            </p>

            <h2
              dir="ltr"
              className="mt-1 break-words text-2xl font-bold text-slate-900 dark:text-white"
            >
              {review.cvName}
            </h2>

            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              {t('review.evaluatedFor')}{' '}
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                {review.jobRequirement}
              </span>
            </p>
          </div>

          <div className="shrink-0">
            <StatusBadge status={review.status} />
          </div>
        </div>
      </div>

      <div className="space-y-8 p-6">

        {/* RAG Summary */}
        <section>
          <div className="mb-3 flex items-center gap-3">
            <div className="h-5 w-1 rounded-full bg-blue-500" />

            <h3 className="font-bold text-slate-900 dark:text-white">
              {t('review.ragSummary')}
            </h3>
          </div>

          <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-5 dark:border-blue-900 dark:bg-blue-950/30">
            <p className="whitespace-pre-wrap leading-7 text-slate-700 dark:text-slate-300">
              {review.ragSummary || t('review.noRagSummary')}
            </p>
          </div>
        </section>

        {/* Strengths */}
        <section>
          <h3 className="mb-4 font-bold text-slate-900 dark:text-white">
            {t('review.strengths')}
          </h3>

          {review.strengths.length > 0 ? (
            <div className="space-y-3">
              {review.strengths.map((strength, index) => (
                <div
                  key={`${strength}-${index}`}
                  className="flex items-start gap-3 rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950/30"
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 text-green-700 dark:text-green-300">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  </span>

                  <p className="text-sm leading-6 text-green-800 dark:text-green-200">
                    {strength}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t('review.noStrengths')}
            </p>
          )}
        </section>

        {/* Matching Requirements */}
        <section>
          <h3 className="mb-4 font-bold text-slate-900 dark:text-white">
            {t('review.matchingRequirements')}
          </h3>

          {review.matchingRequirements.length > 0 ? (
            <div className="space-y-3">
              {review.matchingRequirements.map((requirement, index) => (
                <div
                  key={`${requirement}-${index}`}
                  className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/30"
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 text-blue-700 dark:text-blue-300">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  </span>

                  <p className="text-sm leading-6 text-blue-800 dark:text-blue-200">
                    {requirement}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t('review.noMatchingRequirements')}
            </p>
          )}
        </section>

        {/* Missing Requirements */}
        <section>
          <h3 className="mb-4 font-bold text-slate-900 dark:text-white">
            {t('review.missingRequirements')}
          </h3>

          {review.missingRequirements.length > 0 ? (
            <div className="space-y-3">
              {review.missingRequirements.map((requirement, index) => (
                <div
                  key={`${requirement}-${index}`}
                  className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/30"
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-100 text-sm font-bold text-red-700 dark:bg-red-900 dark:text-red-300">
                    !
                  </span>

                  <p className="text-sm leading-6 text-red-800 dark:text-red-200">
                    {requirement}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950/30">
              <p className="text-sm font-medium text-green-700 dark:text-green-300">
                {t('review.noMissingRequirements')}
              </p>
            </div>
          )}
        </section>

        {/* Rejection Reason */}
        {review.rejectionReason && (
          <section>
            <h3 className="mb-4 font-bold text-slate-900 dark:text-white">
              {t('review.rejectionReason')}
            </h3>

            <div className="rounded-xl border border-red-200 bg-red-50 p-5 dark:border-red-900 dark:bg-red-950/30">
              <p className="leading-7 text-red-800 dark:text-red-200">
                {review.rejectionReason}
              </p>
            </div>
          </section>
        )}

        {/* Metadata */}
        <section className="border-t border-slate-200 pt-6 dark:border-slate-800">
          <div className="grid gap-4 sm:grid-cols-2">

            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {t('review.processedDate')}
              </p>

              <p
                dir="ltr"
                className="mt-2 text-sm font-semibold text-slate-700 dark:text-slate-200"
              >
                {review.createdAt}
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {t('review.jobRequirement')}
              </p>

              <p className="mt-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
                {review.jobRequirement}
              </p>
            </div>

          </div>
        </section>

        {/* Original CV */}
        {fileUrl && (
          <section>
            <button
              type="button"
              onClick={() => setShowPreview(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="h-4 w-4"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M14 3h7v7"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10 14 21 3"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"
                />
              </svg>

              {t('review.viewOriginalCv')}
            </button>
          </section>
        )}

        {fileUrlError && (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('review.noFileAvailable')}
          </p>
        )}

      </div>
    </div>

    {showPreview && fileUrl && (
      <CvPreviewModal fileUrl={fileUrl} cvName={review.cvName} onClose={() => setShowPreview(false)} />
    )}
    </>
  )
}

export default CvDetail