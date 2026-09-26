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

  const loadReviews = async (isPolling = false) => {
    if (!isPolling) setLoading(true)
    try {
      const result = await api.listReviews('?page=1&page_size=100&sort=newest')
      const readyReviews = result.items.filter(review => !(review.status === 'needs_human_review' && !review.ragSummary))
      setReviews(result.items)
      if (!isPolling) {
        setSelectedId((current) => current && readyReviews.some((item) => item.id === current) ? current : readyReviews[0]?.id || null)
        setError('')
      }
    } catch (loadError) {
      if (!isPolling) setError(loadError instanceof Error ? loadError.message : 'Unable to load reviews')
    } finally {
      if (!isPolling) setLoading(false)
    }
  }

  useEffect(() => {
    void loadReviews()
    const intervalId = setInterval(() => {
      void loadReviews(true)
    }, 5000)
    return () => clearInterval(intervalId)
  }, [])

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
    <div className="relative py-6 sm:py-10 transition-all duration-300 ease-out animate-pop-in">
      
      {/* Background Glow Effect */}
      <div className="absolute -top-10 start-1/2 -z-10 h-72 w-72 -translate-x-1/2 rounded-full bg-blue-500/10 blur-3xl dark:bg-blue-600/10 pointer-events-none" />

      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="mb-4 inline-flex rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-300">
            {t('review.badge')}
          </p>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white sm:text-4xl">{t('review.title')}</h1>
          <p className="mt-3 text-slate-600 dark:text-slate-400">{t('review.description')}</p>
        </div>
        <button 
          type="button" 
          onClick={() => void loadReviews()} 
          className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          {t('review.refresh')}
        </button>
      </div>

      {error && (
        <p role="alert" className="mb-6 rounded-xl bg-red-50 p-4 text-red-700 dark:bg-red-950/50 dark:border dark:border-red-900 dark:text-red-300 animate-pop-in">
          {error}
        </p>
      )}

      {loading ? (
        <div className="py-16 text-center animate-pop-in">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" role="status"></div>
          <p className="mt-4 text-slate-600 dark:text-slate-400">Loading reviews...</p>
        </div>
      ) : (
        <>
          <div className="mb-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl bg-green-50 p-5 transition-transform duration-300 hover:scale-[1.02] dark:bg-green-950/40 dark:border dark:border-green-900/60">
              <p className="text-sm font-medium text-green-800 dark:text-green-300">{t('review.approved')}</p>
              <strong className="text-3xl text-green-900 dark:text-green-100">{count('approved')}</strong>
            </div>
            <div className="rounded-2xl bg-amber-50 p-5 transition-transform duration-300 hover:scale-[1.02] dark:bg-amber-950/40 dark:border dark:border-amber-900/60">
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">{t('review.needsHumanReview')}</p>
              <strong className="text-3xl text-amber-900 dark:text-amber-100">{count('needs_human_review')}</strong>
            </div>
            <div className="rounded-2xl bg-red-50 p-5 transition-transform duration-300 hover:scale-[1.02] dark:bg-red-950/40 dark:border dark:border-red-900/60">
              <p className="text-sm font-medium text-red-800 dark:text-red-300">{t('review.notApproved')}</p>
              <strong className="text-3xl text-red-900 dark:text-red-100">{count('not_approved')}</strong>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
            <CvSidebar reviews={reviews} selectedId={selectedId} onSelect={setSelectedId} />
            
            <div key={selectedId || 'empty'} className="min-w-0 transition-all duration-300 ease-out transform animate-pop-in">
              <CvDetail review={selectedReview} />
              {selectedReview && !(selectedReview.status === 'needs_human_review' && !selectedReview.ragSummary) && (
                <HumanReviewActions 
                  review={selectedReview} 
                  onApprove={() => void updateReview('approved', null)} 
                  onReject={(reason) => void updateReview('not_approved', reason)} 
                />
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default ReviewWorkspacePage