import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useSession } from "../../app/session";

const navigation = [
  { to: "/dashboard/kpi", label: "KPI Dashboard", roles: ["Admin", "Manager", "RPL", "ML"] },
  { to: "/dashboard/reports", label: "Custom Reports", roles: ["Admin", "Manager", "RPL"] },
  { to: "/dashboard/ml", label: "ML Dashboard", roles: ["Admin", "Manager", "ML"] },
  { to: "/dashboard/funder", label: "Funder Dashboard", roles: ["Funder", "Admin"] },
  { to: "/dashboard/admin", label: "Admin Dashboard", roles: ["Admin"] },
  { to: "/dashboard/case-studies", label: "Case Studies", roles: ["Admin", "Manager", "RPL", "ML", "Funder"] }
];

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function AppShell() {
  const { user, logout } = useSession();
  const location = useLocation();
  const visibleNavigation = navigation.filter((item) => item.roles.some((role) => user?.roles.includes(role)));
  const currentLabel = visibleNavigation.find((item) => location.pathname.startsWith(item.to))?.label ?? "Dashboard Suite";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <section className="sidebar-block sidebar-profile">
          <span className="sidebar-section-title">Account</span>
          <strong>{`${getGreeting()}, ${user?.name ?? "User"}`}</strong>
          <p className="sidebar-subtext">Regional KPI Dashboard</p>
          <div className="sidebar-meta-list">
            <div className="sidebar-meta-row">
              <span>Role</span>
              <strong>{user?.role ?? "Unknown"}</strong>
            </div>
            <div className="sidebar-meta-row">
              <span>Region</span>
              <strong>{user?.region ?? "Global"}</strong>
            </div>
          </div>
        </section>

        <section className="sidebar-block">
          <span className="sidebar-section-title">View Mode</span>
          <nav className="nav-list">
            {visibleNavigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </section>

        <section className="sidebar-block">
          <span className="sidebar-section-title">Current View</span>
          <p className="sidebar-copy">
            The selected dashboard keeps its own controls and tables, with the sidebar acting as the persistent app rail.
          </p>
          <div className="meta-row">
            <span className="meta-pill">{currentLabel}</span>
          </div>
        </section>

        <div className="refresh-card">
          <span className="refresh-label">Session</span>
          <p className="sidebar-copy">Use the page controls to filter results, then switch views from the sidebar.</p>
          <button className="secondary-button" type="button" onClick={logout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-grid">
            <div className="topbar-copy">
              <span className="eyebrow">Dashboard</span>
              <h2 className="page-title">{currentLabel}</h2>
            </div>
            <div className="meta-row">
              <span className="meta-pill">{user?.role ?? "Unknown"}</span>
              <span className="meta-pill">{user?.region ?? "Global"}</span>
            </div>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
