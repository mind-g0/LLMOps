import { useTranslation } from 'react-i18next'
import StatusBadge from './StatusBadge'
import SimulatedProgress from './SimulatedProgress'
import type { CVReview, ReviewStatus } from '../types/cvReview'

interface CvSidebarProps {
  reviews: CVReview[]
  selectedId: string | null
  onSelect: (id: string) => void
}

const groups: {
  status: ReviewStatus
  translationKey: string
}[] = [
  {
    status: 'needs_human_review',
    translationKey: 'review.needsHumanReview',
  },
  {
    status: 'approved',
    translationKey: 'review.approved',
  },
  {
    status: 'not_approved',
    translationKey: 'review.notApproved',
  },
]

function CvSidebar({
  reviews,
  selectedId,
  onSelect,
}: CvSidebarProps) {
  const { t } = useTranslation()

  return (
    <aside className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">

      {/* Header */}
      <div className="border-b border-slate-200 p-5 dark:border-slate-800">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-bold text-slate-900 dark:text-white">
              {t('review.processedCvs')}
            </h2>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {t('review.selectCv')}
            </p>
          </div>

          <div className="flex h-9 min-w-9 items-center justify-center rounded-full bg-blue-50 px-3 text-sm font-bold text-blue-600 dark:bg-blue-950 dark:text-blue-300">
            {reviews.length}
          </div>
        </div>
      </div>

      {/* Empty State */}
      {reviews.length === 0 ? (
        <div className="p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
            0
          </div>

          <p className="mt-4 font-semibold text-slate-700 dark:text-slate-300">
            {t('review.noProcessedCvs')}
          </p>

          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {t('review.processFromSetup')}
          </p>
        </div>
      ) : (
        <div className="max-h-[700px] overflow-y-auto p-3">

          {groups.map((group) => {
            const groupReviews = reviews.filter(
              (review) => review.status === group.status,
            )

            if (groupReviews.length === 0) {
              return null
            }

            return (
              <div key={group.status} className="mb-6 last:mb-0">

                {/* Group Title */}
                <div className="mb-2 flex items-center justify-between px-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    {t(group.translationKey)}
                  </p>

                  <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                    {groupReviews.length}
                  </span>
                </div>

                {/* CVs */}
                <div className="space-y-2">
                  {groupReviews.map((review) => {
                    const isProcessing = review.status === 'needs_human_review' && !review.ragSummary;
                    const selected = review.id === selectedId

                    if (isProcessing) {
                      return (
                        <div
                          key={review.id}
                          className="w-full flex items-center justify-between gap-3 rounded-xl border border-blue-400 bg-blue-50/50 p-4 shadow-[0_0_10px_rgba(59,130,246,0.3)] animate-pulse dark:border-blue-500 dark:bg-blue-900/20"
                        >
                          <p dir="ltr" className="min-w-0 truncate text-sm font-bold text-slate-900 dark:text-white">
                            {review.cvName}
                          </p>
                          <div className="flex shrink-0 items-center gap-2 text-xs font-bold text-blue-600 dark:text-blue-400">
                            <SimulatedProgress createdAt={review.createdAt} />
                            <svg className="h-5 w-5 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
                          </div>
                        </div>
                      );
                    }

                    return (
                      <button
                        key={review.id}
                        type="button"
                        onClick={() => onSelect(review.id)}
                        className={`w-full rounded-xl border p-4 text-start transition ${
                          selected
                            ? 'border-blue-500 bg-blue-50 shadow-sm dark:border-blue-500 dark:bg-blue-950/40'
                            : 'border-transparent hover:border-slate-200 hover:bg-slate-50 dark:hover:border-slate-700 dark:hover:bg-slate-800'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <p
                            dir="ltr"
                            className="min-w-0 truncate text-sm font-bold text-slate-900 dark:text-white"
                          >
                            {review.cvName}
                          </p>

                          {selected && (
                            <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-blue-500" />
                          )}
                        </div>

                        <div className="mt-3">
                          <StatusBadge status={review.status} />
                        </div>

                        <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-700">
                          <p className="truncate text-xs font-medium text-slate-600 dark:text-slate-300">
                            {review.jobRequirement}
                          </p>

                          <p
                            dir="ltr"
                            className="mt-1 text-xs text-slate-400 dark:text-slate-500"
                          >
                            {review.createdAt}
                          </p>
                        </div>
                      </button>
                    )
                  })}
                </div>

              </div>
            )
          })}

        </div>
      )}
    </aside>
  )
}

export default CvSidebar