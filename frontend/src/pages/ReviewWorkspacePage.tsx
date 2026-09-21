import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import CvSidebar from '../components/CvSidebar'
import CvDetail from '../components/CvDetail'
import HumanReviewActions from '../components/HumanReviewActions'
import { api } from '../api'
import type { CVReview } from '../types/cvReview'

function ReviewWorkspacePage() {
  const { t } = useTranslation()
  const location = useLocation()
  const requestedId = (location.state as { selectedCvId?: string } | null)?.selectedCvId
  const [reviews, setReviews] = useState<CVReview[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(requestedId || null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadReviews = async () => {
    setLoading(true)
    try {
      const result = await api.listReviews('?page=1&page_size=100&sort=newest')
      setReviews(result.items)
      setSelectedId((current) => current && result.items.some((item) => item.id === current) ? current : result.items[0]?.id || null)
      setError('')
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load reviews')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadReviews() }, [])

  const selectedReview = useMemo(() => reviews.find((review) => review.id === selectedId) || null, [reviews, selectedId])
  const updateReview = async (status: 'approved' | 'not_approved', reason: string | null) => {
    if (!selectedReview) return
    try {
      const updated = await api.updateReview(selectedReview.id, status, reason)
      setReviews((current) => current.map((review) => review.id === updated.id ? updated : review))
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Unable to update review')
    }
  }

  const count = (status: CVReview['status']) => reviews.filter((review) => review.status === status).length

  return (
    <div className="py-6 sm:py-10">
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="mb-4 inline-flex rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700">{t('review.badge')}</p>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white sm:text-4xl">{t('review.title')}</h1>
          <p className="mt-3 text-slate-600 dark:text-slate-400">{t('review.description')}</p>
        </div>
        <button type="button" onClick={() => void loadReviews()} className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold dark:border-slate-700 dark:bg-slate-800">{t('review.refresh')}</button>
      </div>
      {error && <p role="alert" className="mb-6 rounded-xl bg-red-50 p-4 text-red-700">{error}</p>}
      {loading ? <p className="py-12 text-center">Loading reviews...</p> : (
        <>
          <div className="mb-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl bg-green-50 p-5"><p>{t('review.approved')}</p><strong className="text-3xl">{count('approved')}</strong></div>
            <div className="rounded-2xl bg-amber-50 p-5"><p>{t('review.needsHumanReview')}</p><strong className="text-3xl">{count('needs_human_review')}</strong></div>
            <div className="rounded-2xl bg-red-50 p-5"><p>{t('review.notApproved')}</p><strong className="text-3xl">{count('not_approved')}</strong></div>
          </div>
          <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
            <CvSidebar reviews={reviews} selectedId={selectedId} onSelect={setSelectedId} />
            <div className="min-w-0">
              <CvDetail review={selectedReview} />
              {selectedReview && <HumanReviewActions review={selectedReview} onApprove={() => void updateReview('approved', null)} onReject={(reason) => void updateReview('not_approved', reason)} />}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default ReviewWorkspacePage
