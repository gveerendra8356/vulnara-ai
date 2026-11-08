import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./components/AppLayout";

import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ScansListPage } from "./pages/ScansListPage";
import { NewScanPage } from "./pages/NewScanPage";
import { ScanDetailPage } from "./pages/ScanDetailPage";
import { VulnerabilityDetailPage } from "./pages/VulnerabilityDetailPage";
import { RemediationQueuePage } from "./pages/RemediationQueuePage";
import { RemediationReviewPage } from "./pages/RemediationReviewPage";
import { AdminConfigPage } from "./pages/AdminConfigPage";
import { AdminCvePage } from "./pages/AdminCvePage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { DepartmentsPage } from "./pages/DepartmentsPage";
import { OrgOverviewPage } from "./pages/OrgOverviewPage";
import { SchedulesPage } from "./pages/SchedulesPage";
import { ProfilePage } from "./pages/ProfilePage";
import { NotFoundPage } from "./pages/NotFoundPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter basename="/vulnara-ai/">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />

            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<DashboardPage />} />
              <Route path="/overview" element={<OrgOverviewPage />} />
              <Route path="/scans" element={<ScansListPage />} />
              <Route path="/scans/new" element={<NewScanPage />} />
              <Route path="/schedules" element={<SchedulesPage />} />
              <Route path="/scans/:scanId" element={<ScanDetailPage />} />
              <Route path="/vulnerabilities/:vulnId" element={<VulnerabilityDetailPage />} />
              <Route path="/remediations" element={<RemediationQueuePage />} />
              <Route path="/remediations/:remediationId" element={<RemediationReviewPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute requireAdmin>
                    <AdminUsersPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/departments"
                element={
                  <ProtectedRoute requireAdmin>
                    <DepartmentsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/config"
                element={
                  <ProtectedRoute requireAdmin>
                    <AdminConfigPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/cve"
                element={
                  <ProtectedRoute requireAdmin>
                    <AdminCvePage />
                  </ProtectedRoute>
                }
              />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
