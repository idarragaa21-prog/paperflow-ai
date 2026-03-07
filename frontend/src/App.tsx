import { useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AuthedLayout from './components/AuthedLayout';
import ProjectLayout from './components/ProjectLayout';
import BooksPage from './pages/BooksPage';
import ClinicalPage from './pages/ClinicalPage';
import ClinicalSheetPage from './pages/ClinicalSheetPage';
// PrivateSourcesPage removed by scope change
import AnalysisPage from './pages/AnalysisPage';
import DraftsPage from './pages/DraftsPage';
import JobsPage from './pages/JobsPage';
import LoginPage from './pages/LoginPage';
import MetaPage from './pages/MetaPage';
import NotesPage from './pages/NotesPage';
import PapersPage from './pages/PapersPage';
import PresentationsPage from './pages/PresentationsPage';
import ProjectsPage from './pages/ProjectsPage';
import ReaderPage from './pages/ReaderPage';
import ReferencesPage from './pages/ReferencesPage';
import ScreeningPage from './pages/ScreeningPage';
import SearchPage from './pages/SearchPage';
import { useAuthStore } from './store/authStore';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const loading = useAuthStore((s) => s.loading);
  if (loading && !user) return <div style={{ padding: 16 }}>Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth);

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
          {/* private sources removed by scope change */}

          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/" element={<Navigate to="/projects" replace />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
