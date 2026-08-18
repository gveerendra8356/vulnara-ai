import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { USE_MOCK } from "../lib/api";

const navItems = [
  { to: "/", label: "Dashboard", icon: "dashboard", end: true },
  { to: "/scans", label: "Scans", icon: "biotech" },
  { to: "/remediations", label: "Remediation Queue", icon: "assignment_turned_in" },
];

const adminItems = [
  { to: "/admin/users", label: "User Management", icon: "group" },
  { to: "/admin/config", label: "Admin Config", icon: "settings" },
  { to: "/admin/cve", label: "CVE Database", icon: "database" },
];

function NavItem({ to, label, icon, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors duration-200 ${
          isActive
            ? "text-primary font-bold border-r-2 border-primary bg-primary-container/10"
            : "text-on-surface-variant hover:bg-surface-variant/50"
        }`
      }
    >
      <span className="material-symbols-outlined text-[20px]">{icon}</span>
      <span>{label}</span>
    </NavLink>
  );
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background text-on-background font-body-md">
      {/* Side Navigation */}
      <nav
        aria-label="Sidebar"
        className="hidden md:flex flex-col justify-between h-screen py-6 bg-surface-container-low w-[260px] fixed left-0 top-0 border-r border-outline-variant z-40"
      >
        <div>
          <div className="px-6 mb-8 flex items-center gap-3">
            <img src="/logo.png" alt="Vulnara" className="h-14 object-contain" />
          </div>

          <div className="px-3 flex flex-col gap-1">
            {navItems.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}

            {user?.role === "admin" && (
              <>
                <div className="px-4 mt-4 mb-1 font-label-caps text-[10px] text-on-surface-variant/60 uppercase tracking-widest">
                  Admin
                </div>
                {adminItems.map((item) => (
                  <NavItem key={item.to} {...item} />
                ))}
              </>
            )}
          </div>
        </div>

        <div className="px-3 flex flex-col gap-1 border-t border-outline-variant/30 pt-4 mx-3">
          {user && (
            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors group ${
                  isActive
                    ? "bg-primary/10 border border-primary/20"
                    : "hover:bg-surface-variant/50"
                }`
              }
            >
              <div className="w-8 h-8 rounded-full border border-primary/30 bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0">
                {user.full_name?.slice(0, 1)?.toUpperCase() || "U"}
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-sm text-on-surface font-medium truncate max-w-[140px]">{user.full_name}</span>
                <span className="text-[10px] uppercase tracking-wider text-on-surface-variant/70 flex items-center gap-1">
                  {user.role}
                  <span className="material-symbols-outlined text-[10px] opacity-0 group-hover:opacity-60 transition-opacity">edit</span>
                </span>
              </div>
            </NavLink>
          )}
          <button
            className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-error font-medium hover:bg-surface-variant/50 transition-colors duration-200 text-left"
            onClick={handleLogout}
          >
            <span className="material-symbols-outlined">logout</span>
            <span>Logout</span>
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <div className="flex-1 ml-0 md:ml-[260px] flex flex-col min-h-screen max-w-full">
        {/* Top App Bar */}
        <header className="flex items-center justify-between h-16 px-6 sticky top-0 z-30 bg-surface/60 backdrop-blur-xl border-b border-outline-variant">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative hidden sm:block w-64 focus-within:ring-1 focus-within:ring-primary rounded-md transition-all">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant/50 text-[18px]">
                search
              </span>
              <input
                className="w-full bg-[#131313] border border-outline-variant rounded-md py-1.5 pl-9 pr-3 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary/50 transition-colors"
                placeholder="Search scans, CVEs..."
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            {USE_MOCK && (
              <span className="font-label-caps text-[10px] bg-primary/20 text-primary px-2 py-1 rounded border border-primary/30 uppercase tracking-wider">
                Mock Mode
              </span>
            )}
            <button className="text-on-surface-variant hover:text-primary transition-all p-2 rounded-full hover:bg-surface-variant/50 relative">
              <span className="material-symbols-outlined">notifications</span>
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-error" />
            </button>
            {user && (
              <div className="w-8 h-8 rounded-full border border-outline-variant bg-surface-variant flex items-center justify-center text-xs font-bold text-primary ml-2">
                {user.full_name?.slice(0, 1)?.toUpperCase() || "U"}
              </div>
            )}
          </div>
        </header>
        <main className="flex-1 w-full">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
