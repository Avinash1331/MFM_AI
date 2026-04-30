import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth.jsx";
import {
  ChartLineUp, Briefcase, Bell, Newspaper, SignOut, Pulse, GridFour,
} from "@phosphor-icons/react";

export default function AppLayout() {
  const { user, ready, logout } = useAuth();
  const location = useLocation();

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div data-testid="layout-loading" className="label-uppercase">Booting terminal...</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;

  const items = [
    { to: "/", icon: GridFour, label: "Overview", end: true, id: "nav-overview" },
    { to: "/portfolio", icon: Briefcase, label: "Portfolio", id: "nav-portfolio" },
    { to: "/alerts", icon: Bell, label: "Alerts", id: "nav-alerts" },
    { to: "/news", icon: Newspaper, label: "News", id: "nav-news" },
  ];

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      {/* Side rail */}
      <aside className="w-56 shrink-0 border-r border-border flex flex-col" data-testid="sidebar">
        <div className="px-4 py-5 border-b border-border flex items-center gap-2">
          <Pulse size={20} weight="bold" className="text-primary" />
          <div>
            <div className="font-black tracking-tighter leading-none">MF.TERMINAL</div>
            <div className="label-uppercase mt-1">v0.1 // intel</div>
          </div>
        </div>
        <nav className="flex-1 py-4">
          {items.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              end={it.end}
              data-testid={it.id}
              className={({ isActive }) =>
                "flex items-center gap-3 px-4 py-2.5 text-sm border-l-2 transition-colors " +
                (isActive
                  ? "border-primary bg-secondary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/60")
              }
            >
              <it.icon size={16} weight="bold" />
              <span className="uppercase tracking-wider text-xs">{it.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-border p-3">
          <div className="text-xs text-muted-foreground truncate" data-testid="user-email">{user.email}</div>
          <button
            onClick={logout}
            data-testid="logout-btn"
            className="mt-2 w-full flex items-center justify-center gap-2 text-xs uppercase tracking-wider border border-border py-2 hover:bg-secondary"
          >
            <SignOut size={14} weight="bold" /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0">
        <header className="border-b border-border px-6 py-3 flex items-center gap-4 bg-card">
          <ChartLineUp size={18} weight="bold" className="text-primary" />
          <div className="label-uppercase">Portfolio Intelligence</div>
          <div className="ml-auto label-uppercase mono">{new Date().toUTCString().slice(5, 25)} UTC</div>
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
