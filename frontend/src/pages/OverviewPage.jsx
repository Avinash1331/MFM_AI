import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtINR, fmtNum, pct } from "../lib/api";
import { usePortfolio } from "../lib/portfolio.jsx";
import { TrendUp, TrendDown, Briefcase, Bell, Warning, Pulse } from "@phosphor-icons/react";

export default function OverviewPage() {
  const { activeId } = usePortfolio() || {};
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [xirr, setXirr] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!activeId) return;
    setData(null); setXirr(null);
    Promise.all([
      api.get("/portfolio", { params: { portfolio_id: activeId } }),
      api.get("/alerts"),
      api.get(`/portfolios/${activeId}/xirr`).catch(() => ({ data: null })),
    ])
      .then(([p, a, x]) => { setData(p.data); setAlerts(a.data); setXirr(x.data); })
      .catch((e) => setErr(e.response?.data?.detail || e.message));
  }, [activeId]);

  if (err) return <div className="text-destructive text-sm" data-testid="overview-error">{err}</div>;
  if (!data) return <div className="label-uppercase" data-testid="overview-loading">Loading...</div>;

  const s = data.summary;
  const positive = s.gain >= 0;

  const tiles = [
    { label: "Invested", value: fmtINR(s.invested), sub: `${s.fund_count} schemes` },
    { label: "Current Value", value: fmtINR(s.current_value), sub: positive ? "Up" : "Down" },
    { label: "Net P&L", value: fmtINR(s.gain), sub: pct(s.gain_pct), pos: positive },
    { label: "XIRR", value: xirr?.xirr_pct != null ? `${fmtNum(xirr.xirr_pct)}%` : "—",
      sub: "annualised", pos: xirr?.xirr_pct != null ? xirr.xirr_pct >= 0 : undefined, icon: Pulse },
    { label: "Active Alerts", value: alerts.length.toString().padStart(2, "0"), sub: "across portfolio" },
  ];

  return (
    <div className="space-y-6" data-testid="overview-page">
      <div className="flex items-baseline justify-between">
        <div>
          <div className="label-uppercase">// Dashboard</div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tighter">Portfolio Overview</h1>
        </div>
        <Link to="/portfolio" className="text-xs uppercase tracking-widest text-primary hover:underline" data-testid="goto-portfolio">
          Manage holdings →
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 ticker-grid">
        {tiles.map((t, i) => (
          <div key={i} className="bg-card p-5" data-testid={`kpi-${i}`}>
            <div className="label-uppercase">{t.label}</div>
            <div className={`mono text-2xl mt-2 ${t.pos === true ? "num-pos" : t.pos === false ? "num-neg" : ""}`}>
              {t.value}
            </div>
            <div className={`text-xs mt-1 ${t.pos === true ? "num-pos" : t.pos === false ? "num-neg" : "text-muted-foreground"}`}>
              {t.sub}
            </div>
          </div>
        ))}
      </div>

      {/* Holdings preview + alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-border">
        <div className="lg:col-span-2 bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="label-uppercase flex items-center gap-2"><Briefcase size={14} weight="bold" /> Holdings</div>
            <div className="label-uppercase mono">{data.holdings.length} schemes</div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs mono" data-testid="holdings-table">
              <thead>
                <tr className="border-b border-border text-muted-foreground uppercase">
                  <th className="text-left py-2 pr-3 font-medium">Scheme</th>
                  <th className="text-right py-2 px-3 font-medium">Units</th>
                  <th className="text-right py-2 px-3 font-medium">NAV</th>
                  <th className="text-right py-2 px-3 font-medium">Value</th>
                  <th className="text-right py-2 pl-3 font-medium">P&amp;L %</th>
                </tr>
              </thead>
              <tbody>
                {data.holdings.map((h) => (
                  <tr key={h.id} className="border-b border-border/50 hover:bg-secondary/30">
                    <td className="py-2.5 pr-3">
                      <Link to={`/fund/${h.fund_id}`} className="hover:text-primary" data-testid={`row-${h.fund_id}`}>
                        <div className="font-sans text-sm font-medium">{h.fund.name}</div>
                        <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{h.fund.category} · {h.fund.amc}</div>
                      </Link>
                    </td>
                    <td className="text-right py-2.5 px-3">{fmtNum(h.units, 2)}</td>
                    <td className="text-right py-2.5 px-3">{fmtNum(h.fund.nav, 2)}</td>
                    <td className="text-right py-2.5 px-3">{fmtINR(h.current_value)}</td>
                    <td className={`text-right py-2.5 pl-3 ${h.gain_pct >= 0 ? "num-pos" : "num-neg"}`}>
                      <span className="inline-flex items-center gap-1 justify-end">
                        {h.gain_pct >= 0 ? <TrendUp size={12} weight="bold" /> : <TrendDown size={12} weight="bold" />}
                        {pct(h.gain_pct)}
                      </span>
                    </td>
                  </tr>
                ))}
                {data.holdings.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">
                    No holdings yet. <Link to="/portfolio" className="text-primary">Add a fund →</Link>
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="label-uppercase flex items-center gap-2"><Bell size={14} weight="bold" /> Recent Alerts</div>
            <Link to="/alerts" className="text-xs uppercase tracking-widest text-primary hover:underline" data-testid="goto-alerts">All →</Link>
          </div>
          <div className="space-y-2" data-testid="alerts-preview">
            {alerts.slice(0, 5).map((a) => (
              <div key={a.id} className="border border-border p-3">
                <div className="flex items-center gap-2">
                  <Warning size={12} weight="bold" className={
                    a.severity === "high" ? "text-destructive"
                      : a.severity === "medium" ? "text-accent" : "text-muted-foreground"
                  } />
                  <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{a.type.replace(/_/g, " ")}</div>
                </div>
                <div className="text-sm font-medium mt-1">{a.title}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{a.fund_name}</div>
              </div>
            ))}
            {alerts.length === 0 && (
              <div className="text-xs text-muted-foreground">No active alerts.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
