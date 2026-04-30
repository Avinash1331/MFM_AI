import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../lib/auth.jsx";
import { usePortfolio } from "../lib/portfolio.jsx";
import { api } from "../lib/api";
import {
  ChartLineUp, Briefcase, Bell, Newspaper, SignOut, Pulse, GridFour,
  Calculator, Receipt, CaretDown, Plus, X, FileArrowUp, GearSix,
} from "@phosphor-icons/react";

export default function AppLayout() {
  const { user, ready, logout } = useAuth();
  const portfolioCtx = usePortfolio();
  const location = useLocation();
  const [pfOpen, setPfOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");

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
  const tools = [
    { to: "/sip", icon: Calculator, label: "SIP Planner", id: "nav-sip" },
    { to: "/tax", icon: Receipt, label: "Tax Report", id: "nav-tax" },
    { to: "/factsheet", icon: FileArrowUp, label: "Factsheet", id: "nav-factsheet" },
    { to: "/settings", icon: GearSix, label: "Settings", id: "nav-settings" },
  ];

  const active = portfolioCtx?.portfolios.find((p) => p.id === portfolioCtx?.activeId);

  const createPf = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    await portfolioCtx.create(newName.trim());
    setNewName(""); setShowCreate(false);
  };

  const deletePf = async (id) => {
    if (!window.confirm("Delete this portfolio and all its holdings?")) return;
    await portfolioCtx.remove(id);
  };

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      <aside className="w-56 shrink-0 border-r border-border flex flex-col" data-testid="sidebar">
        <div className="px-4 py-5 border-b border-border flex items-center gap-2">
          <Pulse size={20} weight="bold" className="text-primary" />
          <div>
            <div className="font-black tracking-tighter leading-none">MF.TERMINAL</div>
            <div className="label-uppercase mt-1">v0.2 // intel</div>
          </div>
        </div>
        <nav className="flex-1 py-4 overflow-y-auto">
          {items.map((it) => (
            <NavLink key={it.to} to={it.to} end={it.end} data-testid={it.id}
              className={({ isActive }) =>
                "flex items-center gap-3 px-4 py-2.5 text-sm border-l-2 transition-colors " +
                (isActive ? "border-primary bg-secondary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/60")}>
              <it.icon size={16} weight="bold" />
              <span className="uppercase tracking-wider text-xs">{it.label}</span>
            </NavLink>
          ))}
          <div className="label-uppercase px-4 mt-5 mb-2">Tools</div>
          {tools.map((it) => (
            <NavLink key={it.to} to={it.to} data-testid={it.id}
              className={({ isActive }) =>
                "flex items-center gap-3 px-4 py-2.5 text-sm border-l-2 transition-colors " +
                (isActive ? "border-primary bg-secondary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/60")}>
              <it.icon size={16} weight="bold" />
              <span className="uppercase tracking-wider text-xs">{it.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-border p-3">
          <div className="text-xs text-muted-foreground truncate" data-testid="user-email">{user.email}</div>
          <button onClick={logout} data-testid="logout-btn"
            className="mt-2 w-full flex items-center justify-center gap-2 text-xs uppercase tracking-wider border border-border py-2 hover:bg-secondary">
            <SignOut size={14} weight="bold" /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <header className="border-b border-border px-6 py-3 flex items-center gap-4 bg-card">
          <ChartLineUp size={18} weight="bold" className="text-primary" />
          <div className="label-uppercase">Portfolio Intelligence</div>

          {/* Portfolio switcher */}
          {portfolioCtx?.portfolios.length > 0 && (
            <div className="relative ml-4">
              <button
                onClick={() => setPfOpen(!pfOpen)}
                data-testid="portfolio-switcher"
                className="flex items-center gap-2 border border-border px-3 py-1.5 text-xs uppercase tracking-widest hover:bg-secondary"
              >
                <Briefcase size={12} weight="bold" />
                <span className="mono normal-case tracking-normal">{active?.name || "—"}</span>
                <CaretDown size={10} weight="bold" />
              </button>
              {pfOpen && (
                <div className="absolute top-full left-0 mt-1 bg-card border border-border min-w-[240px] z-30" data-testid="portfolio-dropdown">
                  {portfolioCtx.portfolios.map((p) => (
                    <div key={p.id} className="flex items-center border-b border-border/50 last:border-b-0">
                      <button
                        onClick={() => { portfolioCtx.setActive(p.id); setPfOpen(false); }}
                        data-testid={`switch-${p.id}`}
                        className={"flex-1 text-left px-3 py-2 text-xs hover:bg-secondary " +
                          (active?.id === p.id ? "text-primary" : "text-foreground")}
                      >
                        <div className="font-medium">{p.name}</div>
                        <div className="text-[10px] uppercase tracking-widest text-muted-foreground mono">{p.fund_count} funds</div>
                      </button>
                      {!p.is_default && (
                        <button onClick={() => deletePf(p.id)} data-testid={`del-pf-${p.id}`}
                                className="px-2 text-muted-foreground hover:text-destructive"><X size={12} /></button>
                      )}
                    </div>
                  ))}
                  <button
                    onClick={() => { setPfOpen(false); setShowCreate(true); }}
                    data-testid="add-portfolio-btn"
                    className="w-full px-3 py-2 text-xs uppercase tracking-widest text-primary hover:bg-secondary border-t border-border flex items-center gap-2"
                  ><Plus size={12} weight="bold" /> New Portfolio</button>
                </div>
              )}
            </div>
          )}

          <div className="ml-auto label-uppercase mono">{new Date().toUTCString().slice(5, 25)} UTC</div>
        </header>
        <div className="p-6"><Outlet /></div>
      </main>

      {showCreate && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50" data-testid="create-pf-modal">
          <form onSubmit={createPf} className="bg-card border border-border max-w-sm w-full p-5 space-y-4">
            <div className="label-uppercase">// New Portfolio</div>
            <input
              autoFocus data-testid="pf-name-input"
              className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm focus:outline-none focus:border-primary"
              placeholder="e.g. Retirement Bucket"
              value={newName} onChange={(e) => setNewName(e.target.value)}
            />
            <div className="flex gap-2">
              <button type="button" onClick={() => setShowCreate(false)}
                className="flex-1 border border-border py-2 text-xs uppercase tracking-widest">Cancel</button>
              <button type="submit" data-testid="pf-create-submit"
                className="flex-1 bg-primary text-primary-foreground py-2 text-xs uppercase tracking-widest font-bold">Create</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
