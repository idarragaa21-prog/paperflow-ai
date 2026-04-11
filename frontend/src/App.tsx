import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import './App.css';
import ErrorBoundary from './components/ErrorBoundary';
import { ThemeProvider } from './components/ThemeProvider';
import { useAuthStore } from './store/authStore';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const SignupPage = lazy(() => import('./pages/SignupPage'));
const ProjectInvitationPage = lazy(() => import('./pages/ProjectInvitationPage'));
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));
const AuthedLayout = lazy(() => import('./components/AuthedLayout'));
const ProjectLayout = lazy(() => import('./components/ProjectLayout'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ProjectsPage = lazy(() => import('./pages/ProjectsPage'));
const JobsPage = lazy(() => import('./pages/JobsPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const CollaborationPage = lazy(() => import('./pages/CollaborationPage'));
const SearchPage = lazy(() => import('./pages/SearchPage'));
const PapersPage = lazy(() => import('./pages/PapersPage'));
const ReaderPage = lazy(() => import('./pages/ReaderPage'));
const MetaPage = lazy(() => import('./pages/MetaPage'));
const MatrixPage = lazy(() => import('./pages/MatrixPage'));
const MetaRunsPage = lazy(() => import('./pages/MetaRunsPage'));
const ArtifactsPage = lazy(() => import('./pages/ArtifactsPage'));
const ReferencesPage = lazy(() => import('./pages/ReferencesPage'));
const WritingAssistantPage = lazy(() => import('./pages/WritingAssistantPage'));
const ClinicalPage = lazy(() => import('./pages/ClinicalPage'));
const DeepResearchPage = lazy(() => import('./pages/DeepResearchPage'));

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
  const initialized = useAuthStore((s) => s.initialized);
  if (!initialized || (loading && !user)) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth);
  useEffect(() => { checkAuth(); }, [checkAuth]);

  return (
    <ThemeProvider>
    <ErrorBoundary>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/project-invitations/:token" element={<ProjectInvitationPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />

            {/* Authenticated routes */}
            <Route element={<RequireAuth><AuthedLayout /></RequireAuth>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/:projectId" element={<ProjectLayout />}>
                <Route index element={<Navigate to="research" replace />} />
                {/* Canonical project workflow paths */}
                <Route path="research" element={<SearchPage />} />
                <Route path="library" element={<PapersPage />} />
                <Route path="reader" element={<ReaderPage />} />
                <Route path="extraction" element={<MetaPage />} />
                <Route path="matrix" element={<MatrixPage />} />
                <Route path="meta-runs" element={<MetaRunsPage />} />
                <Route path="artifacts" element={<ArtifactsPage />} />
                <Route path="references" element={<ReferencesPage />} />
                <Route path="writing" element={<WritingAssistantPage />} />
                <Route path="clinical-consults" element={<ClinicalPage />} />
                <Route path="collaboration" element={<CollaborationPage />} />
              </Route>
              <Route path="/clinical" element={<ClinicalPage />} />
              <Route path="/deep-research" element={<DeepResearchPage />} />
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
    </ThemeProvider>
  );
}
