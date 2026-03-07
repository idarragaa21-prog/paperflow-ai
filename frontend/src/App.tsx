import { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AuthedLayout from './components/AuthedLayout';
import ProjectLayout from './components/ProjectLayout';
// PrivateSourcesPage removed by scope change
import AnalysisPage from './pages/AnalysisPage';
import DraftsPage from './pages/DraftsPage';
import JobsPage from './pages/JobsPage';
import LoginPage from './pages/LoginPage';
import MetaPage from './pages/MetaPage';
import NotesPage from './pages/NotesPage';
import PapersPage from './pages/PapersPage';
import CollaborationPage from './pages/CollaborationPage';
import ProjectsPage from './pages/ProjectsPage';
import ReaderPage from './pages/ReaderPage';
import ReferencesPage from './pages/ReferencesPage';
import ScreeningPage from './pages/ScreeningPage';
import SearchPage from './pages/SearchPage';
import { useAuthStore } from './store/authStore';

const BooksPage = lazy(() => import('./pages/BooksPage'));
const ClinicalPage = lazy(() => import('./pages/ClinicalPage'));
const ClinicalSheetPage = lazy(() => import('./pages/ClinicalSheetPage'));
const PresentationsPage = lazy(() => import('./pages/PresentationsPage'));

function RequireAuth({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const loading = useAuthStore((s) => s.loading);
  if (loading && !user) return <div style={{ padding: 16 }}>Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RouteFallback() {
  return <div style={{ padding: 16 }}>Loading module…</div>;
}

function withSuspense(element: React.ReactNode) {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>;
}

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth);
  const legacyEnabled = import.meta.env.VITE_ENABLE_LEGACY_MODULES === 'true';

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          element={
            <RequireAuth>
              <AuthedLayout />
            </RequireAuth>
          }
        >
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectLayout />}>
            <Route index element={<Navigate to="research" replace />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="research" element={<SearchPage />} />
            <Route path="reader" element={<ReaderPage />} />
            <Route path="papers" element={<PapersPage />} />
            <Route path="library" element={<PapersPage />} />
            <Route path="notes" element={<NotesPage />} />
            <Route path="meta" element={<MetaPage />} />
            <Route path="references" element={<ReferencesPage />} />
            <Route path="drafts" element={<DraftsPage />} />
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="screening" element={<ScreeningPage />} />
            <Route path="collaboration" element={<CollaborationPage />} />
            {legacyEnabled ? <Route path="presentations" element={withSuspense(<PresentationsPage />)} /> : null}
          </Route>

          {legacyEnabled ? <Route path="/clinical" element={withSuspense(<ClinicalPage />)} /> : null}
          {legacyEnabled ? <Route path="/clinical/sheets/:sheetId" element={withSuspense(<ClinicalSheetPage />)} /> : null}
          {legacyEnabled ? <Route path="/books" element={withSuspense(<BooksPage />)} /> : null}
          {/* private sources removed by scope change */}

          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/" element={<Navigate to="/projects" replace />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
