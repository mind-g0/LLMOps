import { useTranslation } from 'react-i18next'
import type { ReviewStatus } from '../types/cvReview'

interface StatusBadgeProps {
  status: ReviewStatus
}

const statusConfig = {
  approved: {
    translationKey: 'review.approved',
    dot: 'bg-green-500',
    style:
      'border-green-200 bg-green-50 text-green-700 dark:border-green-900 dark:bg-green-950/50 dark:text-green-300',
  },

  needs_human_review: {
    translationKey: 'review.needsHumanReview',
    dot: 'bg-amber-500',
    style:
      'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300',
  },

  not_approved: {
    translationKey: 'review.notApproved',
    dot: 'bg-red-500',
    style:
      'border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300',
  },
}

function StatusBadge({ status }: StatusBadgeProps) {
  const { t } = useTranslation()
  const config = statusConfig[status]

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${config.style}`}
    >
      <span className={`h-2 w-2 rounded-full ${config.dot}`} />
      {t(config.translationKey)}
    </span>
  )
}

export default StatusBadge