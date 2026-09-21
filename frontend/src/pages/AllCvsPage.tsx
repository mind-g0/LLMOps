import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import StatusBadge from '../components/StatusBadge'
import { api } from '../api'

import type { CVReview, ReviewStatus } from '../types/cvReview'

const ITEMS_PER_PAGE = 3

function AllCvsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [reviews, setReviews] = useState<CVReview[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | 'all'>('all')
  const [jobFilter, setJobFilter] = useState('all')
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest')
  const [page, setPage] = useState(1)

  const loadReviews = async () => {
    setLoading(true)
    try {
      const result = await api.listReviews('?page=1&page_size=100&sort=newest')
      setReviews(result.items)
      setError('')
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load CVs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadReviews() }, [])

  const jobs = useMemo(
    () => [...new Set(reviews.map((review) => review.jobRequirement))],
    [reviews],
  )

  const filteredReviews = useMemo(() => {
    const result = reviews.filter((review) => {
      const matchesSearch = review.cvName
        .toLowerCase()
        .includes(search.toLowerCase())

      const matchesStatus =
        statusFilter === 'all' || review.status === statusFilter

      const matchesJob =
        jobFilter === 'all' ||
        review.jobRequirement === jobFilter

      return matchesSearch && matchesStatus && matchesJob
    })

    return [...result].sort((a, b) => {
      const first = new Date(a.createdAt).getTime()
      const second = new Date(b.createdAt).getTime()

      return sortOrder === 'newest'
        ? second - first
        : first - second
    })
  }, [reviews, search, statusFilter, jobFilter, sortOrder])

  const totalPages = Math.max(
    1,
    Math.ceil(filteredReviews.length / ITEMS_PER_PAGE),
  )

  const currentPage = Math.min(page, totalPages)

  const paginatedReviews = filteredReviews.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE,
  )

  const resetPage = () => {
    setPage(1)
  }

  const handleDetails = (id: string) => {
    navigate('/review', {
      state: {
        selectedCvId: id,
      },
    })
  }

  return (
    <div className="py-6 sm:py-10">

      {/* Header */}
      <div className="mb-8">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-300">
          <span className="h-2 w-2 rounded-full bg-blue-500" />
          {t('allCvs.badge')}
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-4xl">
          {t('allCvs.title')}
        </h1>

        <p className="mt-3 max-w-3xl text-slate-600 dark:text-slate-400">
          {t('allCvs.description')}
        </p>
      </div>

      {/* Loading */}
      {loading && <p className="py-12 text-center">Loading CVs...</p>}

      {/* Error */}
      {error && <p role="alert" className="mb-6 rounded-xl bg-red-50 p-4 text-red-700">{error}</p>}

      {/* Content */}
      {!loading && (
        <>
          {/* Filters */}
          <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">

              <input
                type="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value)
                  resetPage()
                }}
                placeholder={t('allCvs.searchPlaceholder')}
                className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />

              <select
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(
                    event.target.value as ReviewStatus | 'all',
                  )
                  resetPage()
                }}
                className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                <option value="all">
                  {t('allCvs.allStatuses')}
                </option>

                <option value="approved">
                  {t('review.approved')}
                </option>

                <option value="needs_human_review">
                  {t('review.needsHumanReview')}
                </option>

                <option value="not_approved">
                  {t('review.notApproved')}
                </option>
              </select>

              <select
                value={jobFilter}
                onChange={(event) => {
                  setJobFilter(event.target.value)
                  resetPage()
                }}
                className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                <option value="all">
                  {t('allCvs.allJobs')}
                </option>

                {jobs.map((job) => (
                  <option key={job} value={job}>
                    {job}
                  </option>
                ))}
              </select>

              <select
                value={sortOrder}
                onChange={(event) => {
                  setSortOrder(
                    event.target.value as 'newest' | 'oldest',
                  )
                  resetPage()
                }}
                className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                <option value="newest">
                  {t('allCvs.newestFirst')}
                </option>

                <option value="oldest">
                  {t('allCvs.oldestFirst')}
                </option>
              </select>

            </div>
          </div>

          {/* Results Count */}
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t('allCvs.showing')}{' '}
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                {filteredReviews.length}
              </span>{' '}
              {t('allCvs.cvs')}
            </p>
          </div>

          {/* Empty State */}
          {filteredReviews.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h2 className="font-bold text-slate-900 dark:text-white">
                {t('allCvs.noCvsFound')}
              </h2>

              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                {t('allCvs.tryChangingFilters')}
              </p>
            </div>
          ) : (
            <>

              {/* Desktop Table */}
              <div className="hidden overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900 md:block">
                <div className="overflow-x-auto">
                  <table className="w-full text-start">

                    <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/60">
                      <tr className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        <th className="px-5 py-4">
                          {t('allCvs.cvName')}
                        </th>

                        <th className="px-5 py-4">
                          {t('allCvs.status')}
                        </th>

                        <th className="px-5 py-4">
                          {t('allCvs.job')}
                        </th>

                        <th className="px-5 py-4">
                          {t('review.ragSummary')}
                        </th>

                        <th className="px-5 py-4">
                          {t('review.rejectionReason')}
                        </th>

                        <th className="px-5 py-4">
                          {t('allCvs.date')}
                        </th>

                        <th className="px-5 py-4">
                          {t('allCvs.action')}
                        </th>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                      {paginatedReviews.map((review) => (
                        <tr
                          key={review.id}
                          className="transition hover:bg-slate-50 dark:hover:bg-slate-800/50"
                        >
                          <td
                            dir="ltr"
                            className="px-5 py-5 text-start font-semibold text-slate-900 dark:text-white"
                          >
                            {review.cvName}
                          </td>

                          <td className="px-5 py-5">
                            <StatusBadge status={review.status} />
                          </td>

                          <td className="px-5 py-5 text-sm text-slate-600 dark:text-slate-300">
                            {review.jobRequirement}
                          </td>

                          <td className="max-w-xs px-5 py-5 text-sm text-slate-600 dark:text-slate-400">
                            <p className="line-clamp-2">
                              {review.ragSummary}
                            </p>
                          </td>

                          <td className="max-w-xs px-5 py-5 text-sm text-slate-500 dark:text-slate-400">
                            {review.rejectionReason ?? '—'}
                          </td>

                          <td
                            dir="ltr"
                            className="whitespace-nowrap px-5 py-5 text-start text-sm text-slate-500 dark:text-slate-400"
                          >
                            {review.createdAt}
                          </td>

                          <td className="px-5 py-5">
                            <button
                              type="button"
                              onClick={() => handleDetails(review.id)}
                              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
                            >
                              {t('allCvs.details')}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>

                  </table>
                </div>
              </div>

              {/* Mobile Cards */}
              <div className="grid gap-4 md:hidden">
                {paginatedReviews.map((review) => (
                  <article
                    key={review.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
                  >
                    <div className="flex flex-col gap-3">
                      <div>
                        <h2
                          dir="ltr"
                          className="break-words text-start font-bold text-slate-900 dark:text-white"
                        >
                          {review.cvName}
                        </h2>

                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                          {review.jobRequirement}
                        </p>
                      </div>

                      <div>
                        <StatusBadge status={review.status} />
                      </div>
                    </div>

                    <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-800">
                      <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        {t('review.ragSummary')}
                      </p>

                      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                        {review.ragSummary}
                      </p>
                    </div>

                    {review.rejectionReason && (
                      <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 dark:border-red-900 dark:bg-red-950/30">
                        <p className="text-xs font-bold uppercase text-red-600 dark:text-red-400">
                          {t('review.rejectionReason')}
                        </p>

                        <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                          {review.rejectionReason}
                        </p>
                      </div>
                    )}

                    <div className="mt-5 flex items-center justify-between gap-4">
                      <p
                        dir="ltr"
                        className="text-xs text-slate-400"
                      >
                        {review.createdAt}
                      </p>

                      <button
                        type="button"
                        onClick={() => handleDetails(review.id)}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
                      >
                        {t('allCvs.details')}
                      </button>
                    </div>
                  </article>
                ))}
              </div>

              {/* Pagination */}
              <div className="mt-6 flex flex-col items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row">

                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t('allCvs.page')}{' '}
                  <span className="font-semibold text-slate-700 dark:text-slate-200">
                    {currentPage}
                  </span>{' '}
                  {t('allCvs.of')} {totalPages}
                </p>

                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={currentPage === 1}
                    onClick={() =>
                      setPage((current) => Math.max(1, current - 1))
                    }
                    className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                  >
                    {t('allCvs.previous')}
                  </button>

                  <button
                    type="button"
                    disabled={currentPage === totalPages}
                    onClick={() =>
                      setPage((current) =>
                        Math.min(totalPages, current + 1),
                      )
                    }
                    className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                  >
                    {t('allCvs.next')}
                  </button>
                </div>

              </div>

            </>
          )}
        </>
      )}

    </div>
  )
}

export default AllCvsPage