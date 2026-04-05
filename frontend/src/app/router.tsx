import { HashRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "../components/layout/AppShell";
import { AdminDashboardPage } from "../pages/AdminDashboardPage";
import { CaseStudiesPage } from "../pages/CaseStudiesPage";
import { ChangePasswordPage } from "../pages/ChangePasswordPage";
import { FunderDashboardPage } from "../pages/FunderDashboardPage";
import { KPIDashboardPage } from "../pages/KPIDashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { MLDashboardPage } from "../pages/MLDashboardPage";
import { ReportsPage } from "../pages/ReportsPage";
import { useSession } from "./session";

function allowedForPath(pathname: string, roles: string[]) {
  const checks = [
    { prefix: "/dashboard/admin", roles: ["Admin"] },
    { prefix: "/dashboard/funder", roles: ["Funder", "Admin"] },
    { prefix: "/dashboard/ml", roles: ["Admin", "Manager", "ML"] },
    { prefix: "/dashboard/reports", roles: ["Admin", "Manager", "RPL"] },
    { prefix: "/dashboard/kpi", roles: ["Admin", "Manager", "RPL", "ML"] },
    { prefix: "/dashboard/case-studies", roles: ["Admin", "Manager", "RPL", "ML", "Funder"] }
  ];
  const match = checks.find((item) => pathname.startsWith(item.prefix));
  if (!match) {
    return true;
  }
  return match.roles.some((role) => roles.includes(role));
}

function homeForRoles(roles: string[]) {
  if (roles.includes("Admin") || roles.includes("Manager") || roles.includes("RPL")) {
    return "/dashboard/kpi";
  }
  if (roles.includes("ML")) {
    return "/dashboard/ml";
  }
  if (roles.includes("Funder")) {
    return "/dashboard/funder";
  }
  return "/dashboard/kpi";
}

function ProtectedRoute() {
  const { user, isReady } = useSession();
  const location = useLocation();

  if (!isReady) {
    return (
      <main className="page">
        <p className="status-panel">Loading session...</p>
      </main>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (user.force_password_change && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }

  if (location.pathname.startsWith("/dashboard") && !allowedForPath(location.pathname, user.roles)) {
    return <Navigate to={homeForRoles(user.roles)} replace />;
  }

  return <Outlet />;
}

export function AppRouter() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/change-password" element={<ChangePasswordPage />} />
          <Route element={<AppShell />}>
            <Route path="/" element={<Navigate to="/dashboard/kpi" replace />} />
            <Route path="/dashboard/kpi" element={<KPIDashboardPage />} />
            <Route path="/dashboard/reports" element={<ReportsPage />} />
            <Route path="/dashboard/ml" element={<MLDashboardPage />} />
            <Route path="/dashboard/funder" element={<FunderDashboardPage />} />
            <Route path="/dashboard/admin" element={<AdminDashboardPage />} />
            <Route path="/dashboard/case-studies" element={<CaseStudiesPage />} />
          </Route>
        </Route>
      </Routes>
    </HashRouter>
  );
}
