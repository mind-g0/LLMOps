import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

function AppLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const { t, i18n } = useTranslation()

  const isArabic = i18n.language.startsWith('ar')

  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('theme') === 'dark'
  })

  useEffect(() => {
    const root = document.documentElement

    if (darkMode) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [darkMode])

  const toggleLanguage = async () => {
    const newLanguage = isArabic ? 'en' : 'ar'
    await i18n.changeLanguage(newLanguage)
  }

  const linkStyle = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-5 py-3 text-lg font-semibold transition ${
      isActive
        ? 'bg-blue-600 text-white'
        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'
    }`

  const mobileLinkStyle = ({
    isActive,
  }: {
    isActive: boolean
  }) =>
    `block w-full rounded-lg px-4 py-4 text-lg font-semibold transition ${
      isActive
        ? 'bg-blue-600 text-white'
        : 'text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
    }`

  const closeMobileMenu = () => {
    setMobileMenuOpen(false)
  }

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-slate-50 transition-colors duration-300 dark:bg-slate-950
      [background-image:repeating-linear-gradient(-35deg,theme(colors.blue.200),theme(colors.blue.200)_100px,transparent_100px,transparent_2000px),repeating-linear-gradient(-35deg,transparent,transparent_800px,theme(colors.blue.200)_800px,theme(colors.blue.200)_900px,transparent_900px,transparent_2000px)]
      [background-size:200%_200%,200%_200%]
      [background-position:100%_0%,100%_0%]
      
      dark:[background-image:repeating-linear-gradient(-35deg,theme(colors.blue.800),theme(colors.blue.800)_100px,transparent_100px,transparent_2000px),repeating-linear-gradient(-35deg,transparent,transparent_800px,theme(colors.blue.800)_800px,theme(colors.blue.800)_900px,transparent_900px,transparent_2000px)]
      dark:[background-size:200%_200%,200%_200%]
      dark:[background-position:100%_0%,100%_0%]">

      {/* Background Ambient Glows Everywhere */}
      <div className="pointer-events-none absolute -left-40 -top-40 h-[32rem] w-[32rem] rounded-full bg-sky-300/20 blur-[150px] dark:bg-sky-500/10" />
      <div className="pointer-events-none absolute -right-40 top-1/4 h-[30rem] w-[30rem] rounded-full bg-blue-300/20 blur-[150px] dark:bg-blue-600/10" />
      <div className="pointer-events-none absolute left-1/3 top-2/3 h-[35rem] w-[35rem] rounded-full bg-cyan-300/15 blur-[160px] dark:bg-cyan-500/10" />
      <div className="pointer-events-none absolute -right-40 -bottom-40 h-[32rem] w-[32rem] rounded-full bg-indigo-300/20 blur-[150px] dark:bg-indigo-600/10" />

      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur transition-colors dark:border-slate-800 dark:bg-slate-900/95">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          {/* Logo */}
          <NavLink
            to="/"
            onClick={closeMobileMenu}
            className="flex shrink-0 items-center"
          >
            {/* Light Mode Logo */}
            <img
              src="/hr-ai-logo.png"
              alt="HR AI"
              className="h-14 w-auto object-contain sm:h-23 dark:hidden"
            />

            {/* Dark Mode Logo */}
            <img
              src="/hr-ai-logo-dark.png"
              alt="HR AI"
              className="hidden h-14 w-auto object-contain sm:h-23 dark:block"
            />
          </NavLink>

          {/* Desktop Navigation */}
          <nav className="hidden items-center gap-3 md:flex">
            <NavLink to="/" className={linkStyle}>
              {t('nav.home')}
            </NavLink>
            <NavLink to="/setup" className={linkStyle}>
              {t('nav.setup')}
            </NavLink>
            <NavLink to="/review" className={linkStyle}>
              {t('nav.review')}
            </NavLink>
            <NavLink to="/cvs" className={linkStyle}>
              {t('nav.allCvs')}
            </NavLink>
          </nav>

          {/* Desktop Actions */}
          <div className="hidden items-center gap-3 md:flex">
            {/* Language */}
            <button
              type="button"
              onClick={toggleLanguage}
              className="flex h-12 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-lg font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-blue-800 dark:hover:bg-blue-950/50 dark:hover:text-blue-300"
              aria-label={
                isArabic
                  ? 'Switch to English'
                  : 'التبديل إلى العربية'
              }
              title={
                isArabic
                  ? 'Switch to English'
                  : 'التبديل إلى العربية'
              }
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="h-6 w-6"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18" />
                <path d="M12 3c2.5 2.5 4 5.5 4 9s-1.5 6.5-4 9" />
                <path d="M12 3c-2.5 2.5-4 5.5-4 9s1.5 6.5 4 9" />
              </svg>
              <span>
                {isArabic ? 'EN' : 'AR'}
              </span>
            </button>

            {/* Dark Mode */}
            <button
              type="button"
              onClick={() =>
                setDarkMode((current) => !current)
              }
              className="flex h-12 w-12 items-center justify-center rounded-lg border border-slate-200 bg-white text-lg transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              aria-label="Toggle dark mode"
              title={
                darkMode
                  ? 'Switch to light mode'
                  : 'Switch to dark mode'
              }
            >
              {darkMode ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2" />
                  <path d="M12 20v2" />
                  <path d="m4.93 4.93 1.41 1.41" />
                  <path d="m17.66 17.66 1.41 1.41" />
                  <path d="M2 12h2" />
                  <path d="M20 12h2" />
                  <path d="m6.34 17.66-1.41 1.41" />
                  <path d="m19.07 4.93-1.41 1.41" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
                  <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
                </svg>
              )}
            </button>
          </div>

          {/* Mobile Actions */}
          <div className="flex items-center gap-2 md:hidden">
            <button
              type="button"
              onClick={toggleLanguage}
              className="flex h-12 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 text-lg font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              aria-label={
                isArabic
                  ? 'Switch to English'
                  : 'التبديل إلى العربية'
              }
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="h-6 w-6"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18" />
                <path d="M12 3c2.5 2.5 4 5.5 4 9s-1.5 6.5-4 9" />
                <path d="M12 3c-2.5 2.5-4 5.5-4 9s1.5 6.5 4 9" />
              </svg>
              <span>
                {isArabic ? 'EN' : 'AR'}
              </span>
            </button>
            <button
              type="button"
              onClick={() =>
                setDarkMode((current) => !current)
              }
              className="flex h-12 w-12 items-center justify-center rounded-lg border border-slate-200 bg-white text-lg transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              aria-label="Toggle dark mode"
            >
              {darkMode ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2" />
                  <path d="M12 20v2" />
                  <path d="m4.93 4.93 1.41 1.41" />
                  <path d="m17.66 17.66 1.41 1.41" />
                  <path d="M2 12h2" />
                  <path d="M20 12h2" />
                  <path d="m6.34 17.66-1.41 1.41" />
                  <path d="m19.07 4.93-1.41 1.41" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
                  <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
                </svg>
              )}
            </button>
            <button
              type="button"
              onClick={() =>
                setMobileMenuOpen((current) => !current)
              }
              className="flex h-12 w-12 items-center justify-center rounded-lg border border-slate-200 text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
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
                    d="M6 18 18 6M6 6l12 12"
                  />
                </svg>
              ) : (
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
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              )}
            </button>
          </div>
        </div>
        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="border-t border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900 md:hidden">
            <nav className="space-y-2">
              <NavLink
                to="/"
                onClick={closeMobileMenu}
                className={mobileLinkStyle}
              >
                {t('nav.home')}
              </NavLink>
              <NavLink
                to="/setup"
                onClick={closeMobileMenu}
                className={mobileLinkStyle}
              >
                {t('nav.setup')}
              </NavLink>
              <NavLink
                to="/review"
                onClick={closeMobileMenu}
                className={mobileLinkStyle}
              >
                {t('nav.review')}
              </NavLink>
              <NavLink
                to="/cvs"
                onClick={closeMobileMenu}
                className={mobileLinkStyle}
              >
                {t('nav.allCvs')}
              </NavLink>
            </nav>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="relative z-10 mx-auto w-full max-w-7xl flex-1 px-4 py-6 text-slate-900 transition-colors dark:text-slate-100 sm:px-6">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="relative z-10 mt-16 border-t border-slate-200 bg-white transition-colors dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex flex-col items-center justify-between gap-3 text-center md:flex-row">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              © {new Date().getFullYear()} LLMOps. {t('footer.rights')}
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t('footer.collaboration')}{' '}
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                LLMOps
              </span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default AppLayout