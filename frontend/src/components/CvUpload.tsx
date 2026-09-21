import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api'

const MAX_FILES = 10
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB
const ALLOWED_EXTENSIONS = ['pdf', 'docx']

function CvUpload({ jobRequirementId }: { jobRequirementId?: string }) {
  const { t } = useTranslation()

  const inputRef = useRef<HTMLInputElement>(null)

  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 KB'

    const kb = bytes / 1024

    if (kb < 1024) {
      return `${kb.toFixed(1)} KB`
    }

    return `${(kb / 1024).toFixed(2)} MB`
  }

  const getExtension = (fileName: string) => {
    return fileName.split('.').pop()?.toLowerCase() ?? ''
  }

  const addFiles = (newFiles: File[]) => {
    setError('')

    const acceptedFiles: File[] = []
    const errors: string[] = []

    for (const file of newFiles) {
      const extension = getExtension(file.name)

      if (!ALLOWED_EXTENSIONS.includes(extension)) {
        errors.push(
          t('cvUpload.errors.invalidType', {
            fileName: file.name,
          }),
        )
        continue
      }

      if (file.size > MAX_FILE_SIZE) {
        errors.push(
          t('cvUpload.errors.fileTooLarge', {
            fileName: file.name,
          }),
        )
        continue
      }

      const isDuplicate = [...files, ...acceptedFiles].some(
        (existingFile) =>
          existingFile.name === file.name &&
          existingFile.size === file.size,
      )

      if (isDuplicate) {
        errors.push(
          t('cvUpload.errors.duplicate', {
            fileName: file.name,
          }),
        )
        continue
      }

      if (files.length + acceptedFiles.length >= MAX_FILES) {
        errors.push(
          t('cvUpload.errors.maxFiles', {
            count: MAX_FILES,
          }),
        )
        break
      }

      acceptedFiles.push(file)
    }

    if (acceptedFiles.length > 0) {
      setFiles((currentFiles) => [...currentFiles, ...acceptedFiles])
    }

    if (errors.length > 0) {
      setError(errors.join(' '))
    }
  }

  const handleFileInput = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const selectedFiles = Array.from(event.target.files ?? [])

    addFiles(selectedFiles)

    event.target.value = ''
  }

  const handleDragOver = (
    event: React.DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (
    event: React.DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (
    event: React.DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault()
    setIsDragging(false)

    const droppedFiles = Array.from(event.dataTransfer.files)

    addFiles(droppedFiles)
  }

  const removeFile = (indexToRemove: number) => {
    setFiles((currentFiles) =>
      currentFiles.filter((_, index) => index !== indexToRemove),
    )

    setError('')
  }

  const clearAll = () => {
    setFiles([])
    setError('')
  }

  const startProcess = async () => {
    if (!jobRequirementId) {
      setError('Save a job requirement before uploading CVs.')
      return
    }
    setIsUploading(true)
    setError('')
    try {
      await Promise.all(files.map((file) => api.uploadReview(file, jobRequirementId)))
      setFiles([])
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div>

      {/* Section Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
            {t('cvUpload.candidateCvs')}
          </p>

          <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
            {t('cvUpload.title')}
          </h2>

          <p className="mt-2 text-slate-600 dark:text-slate-400">
            {t('cvUpload.description', {
              count: MAX_FILES,
            })}
          </p>
        </div>

        <div className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
          {t('cvUpload.fileCount', {
            current: files.length,
            max: MAX_FILES,
          })}
        </div>
      </div>

      {/* Upload Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-colors dark:border-slate-800 dark:bg-slate-900 sm:p-6">

        {/* Drag & Drop Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition sm:p-12 ${
            isDragging
              ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950/40'
              : 'border-slate-300 bg-slate-50 hover:border-blue-400 hover:bg-blue-50/50 dark:border-slate-700 dark:bg-slate-800/50 dark:hover:border-blue-500 dark:hover:bg-slate-800'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.docx"
            onChange={handleFileInput}
            className="hidden"
          />

          {/* Upload Icon */}
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-300">
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
                d="M12 16V4m0 0L7 9m5-5 5 5M5 20h14"
              />
            </svg>
          </div>

          <h3 className="mt-5 text-lg font-bold text-slate-900 dark:text-white">
            {isDragging
              ? t('cvUpload.dropHere')
              : t('cvUpload.dragDrop')}
          </h3>

          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {t('cvUpload.browse')}
          </p>

          <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
            <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
              PDF
            </span>

            <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
              DOCX
            </span>

            <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
              {t('cvUpload.maxSize')}
            </span>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div
            role="alert"
            className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-100 text-xs font-bold dark:bg-red-900">
                !
              </span>

              <p>{error}</p>
            </div>
          </div>
        )}

        {/* Selected Files */}
        {files.length > 0 && (
          <div className="mt-8">

            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white">
                  {t('cvUpload.selectedCvs')}
                </h3>

                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  {t('cvUpload.reviewBeforeProcess')}
                </p>
              </div>

              <button
                type="button"
                onClick={clearAll}
                className="shrink-0 text-sm font-semibold text-red-600 transition hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              >
                {t('cvUpload.clearAll')}
              </button>
            </div>

            <div className="space-y-3">
              {files.map((file, index) => (
                <div
                  key={`${file.name}-${file.size}-${index}`}
                  className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 transition-colors dark:border-slate-700 dark:bg-slate-800"
                >
                  <div className="flex min-w-0 items-center gap-3">

                    {/* File Icon */}
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
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
                          d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M14 2v6h6"
                        />
                      </svg>
                    </div>

                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
                        {file.name}
                      </p>

                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {formatFileSize(file.size)}
                      </p>
                    </div>
                  </div>

                  {/* Remove */}
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/50 dark:hover:text-red-400"
                    aria-label={t('cvUpload.removeFile', {
                      fileName: file.name,
                    })}
                    title={t('cvUpload.remove')}
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
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Start Process */}
        <div className="mt-8 flex flex-col gap-3 border-t border-slate-200 pt-6 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">

          <p className="text-sm text-slate-500 dark:text-slate-400">
            {files.length === 0
              ? t('cvUpload.addAtLeastOne')
              : t('cvUpload.readyToProcess', {
                  count: files.length,
                })}
          </p>

          <button
            type="button"
            disabled={files.length === 0 || isUploading}
            onClick={startProcess}
            className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 dark:disabled:bg-slate-800 dark:disabled:text-slate-500"
          >
            {isUploading ? 'Uploading...' : t('cvUpload.startProcess')}
          </button>

        </div>
      </div>
    </div>
  )
}

export default CvUpload