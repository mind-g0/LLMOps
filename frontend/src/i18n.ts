import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import ar from './locales/ar.json'

const savedLanguage = localStorage.getItem('language') || 'en'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: en,
      },
      ar: {
        translation: ar,
      },
    },

    lng: savedLanguage,
    fallbackLng: 'en',

    interpolation: {
      escapeValue: false,
    },
  })

const updateDocumentLanguage = (language: string) => {
  const isArabic = language === 'ar'

  document.documentElement.lang = language
  document.documentElement.dir = isArabic ? 'rtl' : 'ltr'
}

updateDocumentLanguage(i18n.language)

i18n.on('languageChanged', (language) => {
  localStorage.setItem('language', language)
  updateDocumentLanguage(language)
})

export default i18n