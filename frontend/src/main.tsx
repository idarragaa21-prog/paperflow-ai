import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import './paperguide.css'
import App from './App.tsx'

// Enable paperguide design system globally
if (typeof document !== 'undefined') {
  document.documentElement.classList.add('pg');
}
import { ToastProvider } from './ui/Toast/ToastProvider'
import { ConfirmProvider } from './ui/Dialog/useConfirm'
import { I18nProvider } from './i18n'
import { ThemeProvider } from './components/ThemeProvider'
import { GlobalErrorBridge } from './components/GlobalErrorBridge'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30 s before refetch
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <I18nProvider>
          <ToastProvider>
            <GlobalErrorBridge />
            <ConfirmProvider>
              <App />
            </ConfirmProvider>
          </ToastProvider>
        </I18nProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
