import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

interface CvPreviewModalProps {
  fileUrl: string
  cvName: string
  onClose: () => void
}

function CvPreviewModal({ fileUrl, cvName, onClose }: CvPreviewModalProps) {
  const { t } = useTranslation()
  const [blobUrl, setBlobUrl] = useState('')
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch(fileUrl)
      .then((res) => {
        if (!res.ok) throw new Error()
        return res.blob()
      })
      .then((blob) => {
        if (!cancelled) setBlobUrl(URL.createObjectURL(blob))
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
    return () => { cancelled = true }
  }, [fileUrl])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <h2 dir="ltr" className="truncate text-lg font-bold text-slate-900 dark:text-white">{cvName}</h2>
          <div className="flex items-center gap-2">
            <a
              href={fileUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0L7 9m5-5 5 5M5 20h14" />
              </svg>
              {t('cvPreview.download')}
            </a>
            <button
              type="button"
              onClick={onClose}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-white"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto bg-slate-100 p-2 dark:bg-slate-800">
          {error ? (
            <div className="flex h-[70vh] items-center justify-center text-sm text-slate-500">
              Unable to load CV preview.
            </div>
          ) : blobUrl ? (
            <iframe
              src={blobUrl}
              title={cvName}
              className="h-full w-full rounded-lg bg-white"
              style={{ minHeight: '70vh' }}
            />
          ) : (
            <div className="flex h-[70vh] items-center justify-center text-sm text-slate-400">
              Loading...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CvPreviewModal