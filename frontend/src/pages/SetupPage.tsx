  import { useState } from 'react'
  import { useTranslation } from 'react-i18next'
  import type { JobRequirement } from '../api'
import JobRequirementCard from '../components/JobRequirementCard'
import CvUpload from '../components/CvUpload'

function SetupPage() {
  const { t } = useTranslation()
  const [selectedJobId, setSelectedJobId] = useState<string>()

  return (
    <div className="py-6 sm:py-10">

      {/* Page Header */}
      <div className="mb-10">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-300">
          <span className="h-2 w-2 rounded-full bg-blue-500" />
          {t('setup.badge')}
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-4xl">
          {t('setup.title')}
        </h1>

        <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-400">
          {t('setup.description')}
        </p>
      </div>

      {/* Job Requirements */}
      <section>
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">

          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
              {t('setup.jobRequirements')}
            </h2>

            <p className="mt-2 text-slate-600 dark:text-slate-400">
              {t('setup.jobRequirementsDescription')}
            </p>
          </div>

          <div className="w-fit rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
            {t('setup.maximumJobs')}
          </div>

        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          {[1, 2, 3].map((number) => (
            <JobRequirementCard
              key={number}
              number={number}
              onSaved={(job: JobRequirement) => setSelectedJobId(job.id)}
            />
          ))}
        </div>
      </section>

      <div className="my-12 border-t border-slate-200 dark:border-slate-800" />

      {/* CV Upload */}
      <section>
        <CvUpload jobRequirementId={selectedJobId} />
      </section>

    </div>
  )
}

export default SetupPage