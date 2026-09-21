import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, type JobRequirement } from '../api'

interface JobRequirementCardProps {
  number: number
  onSaved?: (job: JobRequirement) => void
}

interface JobFormData {
  jobName: string
  jobTitle: string
  description: string
}

function JobRequirementCard({ number, onSaved }: JobRequirementCardProps) {
  const { t } = useTranslation()

  const [isEditing, setIsEditing] = useState(true)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const [formData, setFormData] = useState<JobFormData>({
    jobName: '',
    jobTitle: '',
    description: '',
  })

  const handleChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = event.target

    setFormData((current) => ({
      ...current,
      [name]: value,
    }))
  }

  const handleSave = async () => {
    setError('')
    try {
      const job = await api.createJob({
        name: formData.jobName || `Job ${number}`,
        title: formData.jobTitle,
        description: formData.description,
        requirements: [],
      })
      onSaved?.(job)
      setIsEditing(false)
      setSaved(true)
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unable to save job')
    }
  }

  const handleEdit = () => {
    setIsEditing(true)
  }

  const inputStyle =
    'w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:cursor-not-allowed disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-500 dark:disabled:bg-slate-800/60'

  const labelStyle =
    'mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-300'

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-colors dark:border-slate-800 dark:bg-slate-900">

      {/* Header */}
      <div className="mb-6 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
            {t('jobCard.job')} {number}
          </p>

          <h3 className="mt-1 text-lg font-bold text-slate-900 dark:text-white">
            {t('jobCard.jobRequirement')}
          </h3>
        </div>

        {saved && (
          <button
            type="button"
            onClick={handleEdit}
            disabled={isEditing}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            {t('jobCard.edit')}
          </button>
        )}
      </div>

      {/* Saved Status */}
      {saved && !isEditing && (
        <div className="mb-5 flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-700 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          {t('jobCard.saved')}
        </div>
      )}

      {error && <p className="mb-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <div className="space-y-5">

        {/* Job Name */}
        <div>
          <label className={labelStyle}>
            {t('jobCard.jobName')}
          </label>

          <input
            type="text"
            name="jobName"
            value={formData.jobName}
            onChange={handleChange}
            disabled={!isEditing}
            placeholder={t('jobCard.jobNamePlaceholder')}
            className={inputStyle}
          />
        </div>

        {/* Job Title */}
        <div>
          <label className={labelStyle}>
            {t('jobCard.jobTitle')}
          </label>

          <input
            type="text"
            name="jobTitle"
            value={formData.jobTitle}
            onChange={handleChange}
            disabled={!isEditing}
            placeholder={t('jobCard.jobTitlePlaceholder')}
            className={inputStyle}
          />
        </div>

        {/* Description */}
        <div>
          <label className={labelStyle}>
            {t('jobCard.description')}
          </label>

          <textarea
            name="description"
            value={formData.description}
            onChange={handleChange}
            disabled={!isEditing}
            rows={4}
            placeholder={t('jobCard.descriptionPlaceholder')}
            className={`${inputStyle} resize-none`}
          />
        </div>

      </div>

      {/* Save Button */}
      {isEditing && (
        <button
          type="button"
          onClick={handleSave}
          className="mt-6 w-full rounded-xl bg-blue-600 px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-500/20"
        >
          {saved ? t('jobCard.saveChanges') : t('jobCard.saveJob')}
        </button>
      )}

    </div>
  )
}

export default JobRequirementCard