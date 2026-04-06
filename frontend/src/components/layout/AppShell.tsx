import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useSession } from "../../app/session";
import { useDashboardTheme } from "../../app/theme";

const navigation = [
  { to: "/dashboard/kpi", label: "KPI Dashboard", roles: ["Admin", "Manager", "RPL", "ML"] },
  { to: "/dashboard/reports", label: "Custom Reports", roles: ["Admin", "Manager", "RPL"] },
  { to: "/dashboard/ml", label: "ML Dashboard", roles: ["Admin", "Manager", "ML"] },
  { to: "/dashboard/funder", label: "Funder Dashboard", roles: ["Funder", "Admin"] },
  { to: "/dashboard/admin", label: "Admin Dashboard", roles: ["Admin"] },
  { to: "/dashboard/case-studies", label: "Case Studies", roles: ["Admin", "Manager", "RPL", "ML", "Funder"] }
];

export function AppShell() {
  const { theme, toggleTheme } = useDashboardTheme();
  const { user, logout } = useSession();
  const location = useLocation();
  const visibleNavigation = navigation.filter((item) => item.roles.some((role) => user?.roles.includes(role)));
  const currentLabel = visibleNavigation.find((item) => location.pathname.startsWith(item.to))?.label ?? "Dashboard Suite";
  const badgeTimestamp = Math.floor(Date.now() / 60000);
  const nightlyBadgeUrl = `https://github.com/Scott-MoM/rpl-kpi/actions/workflows/nightly-beacon-sync.yml/badge.svg?branch=main&t=${badgeTimestamp}`;
  const nightlyBadgeLink = "https://github.com/Scott-MoM/rpl-kpi/actions/workflows/nightly-beacon-sync.yml";

  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  function displayName(name?: string | null, email?: string | null) {
    const cleanedName = String(name ?? "").trim();
    if (cleanedName && cleanedName !== String(email ?? "").trim()) {
      return cleanedName;
    }
    if (cleanedName) {
      return cleanedName;
    }
    const localPart = String(email ?? "").split("@")[0].replace(/[._-]+/g, " ").trim();
    if (!localPart) {
      return "User";
    }
    return localPart.replace(/\b\w/g, (char) => char.toUpperCase());
  }

  return (
    <div className="app-shell">
      <aside className="sidebar-panel glass-panel glass-panel-sidebar">
        <section className="sidebar-section">
          <span className="sidebar-section-title">Account</span>
          <strong>{`${getGreeting()}, ${displayName(user?.name, user?.email)}`}</strong>
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

        <section className="sidebar-section">
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

        <section className="sidebar-section">
          <span className="sidebar-section-title">Automation</span>
          <div className="status-badge-rail">
            <a href={nightlyBadgeLink} target="_blank" rel="noreferrer" className="status-badge-link">
              <img src={nightlyBadgeUrl} alt="Nightly Beacon Sync status badge" className="status-badge-image" />
            </a>
          </div>
          <p className="sidebar-copy">
            See the keep-awake monitor on the{" "}
            <a href="https://k62b8n0t.status.cron-job.org/" target="_blank" rel="noreferrer">
              Status Page
            </a>
            .
          </p>
        </section>

        <section className="sidebar-section sidebar-session-section">
          <span className="sidebar-section-title">Session</span>
          <p className="sidebar-copy">Use the page controls to filter results, then switch views from the sidebar.</p>
          <button className="primary-button" type="button" onClick={logout}>
            Logout
          </button>
        </section>
      </aside>

      <main className="controls-column glass-panel glass-panel-controls">
        <header className="topbar controls-topbar">
          <div className="topbar-grid">
            <div className="topbar-copy">
              <span className="eyebrow">Dashboard Controls</span>
              <h2 className="page-title">{currentLabel}</h2>
            </div>
            <div className="meta-row">
              <span className="meta-pill">{user?.role ?? "Unknown"}</span>
              <span className="meta-pill">{user?.region ?? "Global"}</span>
            </div>
          </div>
          <div className="theme-toggle-row">
            <span className="theme-label">Theme</span>
            <button className="secondary-button" type="button" onClick={toggleTheme}>
              {theme === "light" ? "Switch to Dark" : "Switch to Light"}
            </button>
          </div>
        </header>
        <div className="controls-copy">
          <p>Filters, toggles, and helper controls for the active view go here.</p>
          <p>Hover over a section to see more detail.</p>
        </div>
      </main>

      <section className="view-column glass-panel glass-panel-view">
        <header className="topbar topbar-green">
          <div className="topbar-copy">
            <span className="eyebrow">Current View</span>
            <h2 className="page-title">{currentLabel}</h2>
          </div>
        </header>
        <div className="view-content">
          <Outlet />
        </div>
      </section>
    </div>
  );
}
