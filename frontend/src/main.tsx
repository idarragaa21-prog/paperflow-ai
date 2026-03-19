import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ToastProvider } from './ui/Toast/ToastProvider'
import { ConfirmProvider } from './ui/Dialog/useConfirm'
import { I18nProvider } from './i18n'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <ToastProvider>
        <ConfirmProvider>
          <App />
        </ConfirmProvider>
      </ToastProvider>
    </I18nProvider>
  </StrictMode>,
)
