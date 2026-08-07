import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { USE_MOCK } from "../lib/api";

const navItems = [
  { to: "/", label: "Dashboard", icon: "◈", end: true },
  { to: "/scans", label: "Scans", icon: "▤" },
  { to: "/remediations", label: "Remediation Queue", icon: "✓" },
];

const adminItems = [
  { to: "/admin/config", label: "Configuration", icon: "⚙" },
  { to: "/admin/cve", label: "CVE Definitions", icon: "◎" },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">V</div>
          <div>
            <div className="brand-name">Vulnara</div>
            <div className="brand-sub">Vuln Intelligence</div>
          </div>
        </div>

        <div className="nav-section-label">Workspace</div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}

        {user?.role === "admin" && (
          <>
            <div className="nav-section-label">Admin</div>
            {adminItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </>
        )}

        <div style={{ flex: 1 }} />
        <button className="nav-link" style={{ width: "100%", border: "none", background: "none", cursor: "pointer" }} onClick={handleLogout}>
          <span className="nav-icon">⏻</span>
          Sign out
        </button>
      </aside>

      <div className="main-col">
        <div className="topbar">
          <div>
            <div className="topbar-title">Vulnara</div>
            <div className="topbar-crumb">AI-augmented vulnerability intelligence</div>
          </div>
          <div className="topbar-right">
            {USE_MOCK && <span className="mock-banner">MOCK MODE</span>}
            {user && (
              <div className="user-chip">
                <span>{user.full_name}</span>
                <span className="role-pill">{user.role}</span>
              </div>
            )}
          </div>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
