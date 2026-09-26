import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const teamMembers = [
  'Nassir Abdullah Abu Saroor',
  'Abdulrahman Yousef Alanazi',
  'Yaser Abdullah Alshareef',
  'Salman Jaber Alqahtani',
]

const workflowSteps = ['step1', 'step2', 'step3']

function HomePage() {
  const { t } = useTranslation()
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsLoaded(true), 50)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className={`py-6 sm:py-10 transition-all duration-700 ease-out ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>

      {/* Hero */}
      <section className={`relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white px-6 py-20 text-center shadow-sm transition-all duration-1000 ease-out dark:border-slate-800 dark:bg-slate-900 sm:px-10 sm:py-24 lg:px-16 lg:py-28 ${isLoaded ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}>

        {/* Distributed & Lighter Ambient Glows Everywhere */}
        <div className="pointer-events-none absolute -left-20 -top-20 h-96 w-96 rounded-full bg-sky-300/20 blur-[130px] dark:bg-sky-500/15" />
        <div className="pointer-events-none absolute -right-20 -top-20 h-96 w-96 rounded-full bg-blue-300/20 blur-[130px] dark:bg-blue-500/15" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[30rem] w-[30rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-300/20 blur-[150px] dark:bg-cyan-400/10" />
        <div className="pointer-events-none absolute -bottom-20 -left-20 h-96 w-96 rounded-full bg-indigo-300/20 blur-[130px] dark:bg-indigo-600/15" />
        <div className="pointer-events-none absolute -bottom-20 -right-20 h-96 w-96 rounded-full bg-blue-400/20 blur-[130px] dark:bg-blue-600/15" />

        <div className="relative z-10 mx-auto max-w-4xl">

          {/* Badge */}
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-300">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            {t('home.badge')}
          </div>

          {/* HR AI */}
          <h1
            dir="ltr"
            className="text-6xl font-black tracking-tight text-slate-900 dark:text-white sm:text-7xl lg:text-8xl"
          >
            HR{' '}
            <span className="bg-gradient-to-r from-blue-500 to-cyan-400 bg-clip-text text-transparent">
              AI
            </span>
          </h1>

          {/* Technology */}
          <p
            dir="ltr"
            className="mt-5 text-sm font-bold uppercase tracking-[0.3em] text-blue-600 dark:text-blue-400 sm:text-base"
          >
            {t('home.poweredBy')}
          </p>

          {/* Description */}
          <p className="mx-auto mt-7 max-w-3xl text-base leading-8 text-slate-600 dark:text-slate-300 sm:text-lg lg:text-xl">
            {t('home.description')}
          </p>

          {/* Buttons */}
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">

            <Link
              to="/setup"
              className="min-w-44 rounded-xl bg-blue-600 px-7 py-3.5 text-center font-semibold text-white shadow-lg shadow-blue-600/20 transition duration-300 hover:-translate-y-0.5 hover:bg-blue-700 hover:shadow-xl"
            >
              {t('home.startReview')}
            </Link>

            <Link
              to="/cvs"
              className="min-w-44 rounded-xl border border-slate-300 bg-white px-7 py-3.5 text-center font-semibold text-slate-700 transition duration-300 hover:-translate-y-0.5 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              {t('home.viewCvs')}
            </Link>

          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className={`mt-20 transition-all duration-1000 delay-200 ease-out ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>

        <div className="mb-10 text-center">

          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600 dark:text-blue-400">
            {t('home.howItWorks')}
          </p>

          <h2 className="mt-3 text-3xl font-bold text-slate-900 dark:text-white sm:text-4xl">
            {t('home.workflowTitle')}
          </h2>

          <p className="mx-auto mt-4 max-w-2xl leading-7 text-slate-600 dark:text-slate-400">
            {t('home.workflowDescription')}
          </p>

        </div>

        <div className="grid gap-6 md:grid-cols-3">

          {workflowSteps.map((step, index) => (
            <div
              key={step}
              className="group rounded-2xl border border-slate-200 bg-white p-7 shadow-sm transition duration-300 hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg dark:border-slate-800 dark:bg-slate-900 dark:hover:border-blue-900"
            >

              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-sm font-bold text-blue-600 transition group-hover:bg-blue-600 group-hover:text-white dark:bg-blue-950 dark:text-blue-300">
                {String(index + 1).padStart(2, '0')}
              </div>

              <h3 className="mt-6 text-xl font-bold text-slate-900 dark:text-white">
                {t(`home.${step}.title`)}
              </h3>

              <p className="mt-3 leading-7 text-slate-600 dark:text-slate-400">
                {t(`home.${step}.description`)}
              </p>

            </div>
          ))}

        </div>
      </section>

      {/* Team */}
      <section className={`mt-20 transition-all duration-1000 delay-300 ease-out ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>

        <div className="mb-10 text-center">

          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600 dark:text-blue-400">
            {t('home.teamLabel')}
          </p>

          <h2 className="mt-3 text-3xl font-bold text-slate-900 dark:text-white sm:text-4xl">
            {t('home.teamTitle')}
          </h2>

          <p className="mx-auto mt-4 max-w-2xl text-slate-600 dark:text-slate-400">
            {t('home.teamDescription')}
          </p>

        </div>

        <div
          dir="ltr"
          className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4"
        >

          {teamMembers.map((member) => (
            <div
              key={member}
              className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm transition duration-300 hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg dark:border-slate-800 dark:bg-slate-900 dark:hover:border-blue-900"
            >

              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-blue-100 font-bold text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                {member
                  .split(' ')
                  .slice(0, 2)
                  .map((name) => name[0])
                  .join('')}
              </div>

              <h3 className="mt-5 font-bold text-slate-900 dark:text-white">
                {member}
              </h3>

              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                {t('home.teamMember')}
              </p>

            </div>
          ))}

        </div>
      </section>

    </div>
  )
}

export default HomePage