import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import AuthedLayout from './components/AuthedLayout';
import ProjectLayout from './components/ProjectLayout';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';
import { useAuthStore } from './store/authStore';

// Eager: lightweight pages
import DashboardPage from './pages/DashboardPage';
import ProjectsPage from './pages/ProjectsPage';
import JobsPage from './pages/JobsPage';
import SettingsPage from './pages/SettingsPage';

// Lazy: heavy pages (code-split)
const SearchPage = lazy(() => import('./pages/SearchPage'));
const PapersPage = lazy(() => import('./pages/PapersPage'));
const ReaderPage = lazy(() => import('./pages/ReaderPage'));
const NotesPage = lazy(() => import('./pages/NotesPage'));
const MetaPage = lazy(() => import('./pages/MetaPage'));
const ReferencesPage = lazy(() => import('./pages/ReferencesPage'));
const DraftsPage = lazy(() => import('./pages/DraftsPage'));
const PresentationsPage = lazy(() => import('./pages/PresentationsPage'));
const AnalysisPage = lazy(() => import('./pages/AnalysisPage'));
const ScreeningPage = lazy(() => import('./pages/ScreeningPage'));
const ClinicalPage = lazy(() => import('./pages/ClinicalPage'));
const ClinicalSheetPage = lazy(() => import('./pages/ClinicalSheetPage'));
const BooksPage = lazy(() => import('./pages/BooksPage'));

function PageLoader() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200, gap: 10, color: 'var(--rc-muted)' }}>
      <span className="rc-spinner" style={{ width: 18, height: 18 }} />
      Loading…
    </div>
  );
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const loading = useAuthStore((s) => s.loading);
  if (loading && !user) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth);
  useEffect(() => { checkAuth(); }, [checkAuth]);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireAuth><AuthedLayout /></RequireAuth>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/:projectId" element={<ProjectLayout />}>
                <Route index element={<Navigate to="research" replace />} />
                <Route path="search" element={<SearchPage />} />
                <Route path="research" element={<SearchPage />} />
                <Route path="reader" element={<ReaderPage />} />
                <Route path="papers" element={<PapersPage />} />
                <Route path="library" element={<PapersPage />} />
                <Route path="notes" element={<NotesPage />} />
                <Route path="presentations" element={<PresentationsPage />} />
                <Route path="meta" element={<MetaPage />} />
                <Route path="references" element={<ReferencesPage />} />
                <Route path="drafts" element={<DraftsPage />} />
                <Route path="analysis" element={<AnalysisPage />} />
                <Route path="screening" element={<ScreeningPage />} />
              </Route>
              <Route path="/clinical" element={<ClinicalPage />} />
              <Route path="/clinical/sheets/:sheetId" element={<ClinicalSheetPage />} />
              <Route path="/books" element={<BooksPage />} />
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
