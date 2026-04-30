import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Warning, Bell } from "@phosphor-icons/react";

const TYPE_LABEL = {
  manager_change: "Fund Manager Change",
  category_reclassification: "Category Reclassification",
  objective_change: "Objective Change",
  name_change: "Fund Name Change",
  asset_allocation: "Asset Allocation Shift",
};

const SEV_COLOR = {
  high: "border-destructive/60 bg-destructive/5 text-destructive",
  medium: "border-accent/60 bg-accent/5 text-accent",
  low: "border-border text-muted-foreground",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    api.get("/alerts").then((r) => setAlerts(r.data));
  }, []);

  if (!alerts) return <div className="label-uppercase">Loading...</div>;

  const filtered = filter === "all" ? alerts : alerts.filter((a) => a.type === filter);
  const types = ["all", ...Object.keys(TYPE_LABEL)];

  return (
    <div className="space-y-6" data-testid="alerts-page">
      <div>
        <div className="label-uppercase">// Alerts</div>
        <h1 className="text-3xl font-black tracking-tighter">Active Watchdog Signals</h1>
      </div>

      <div className="flex flex-wrap gap-px bg-border">
        {types.map((t) => (
          <button
            key={t}
            data-testid={`filter-${t}`}
            onClick={() => setFilter(t)}
            className={"px-3 py-1.5 text-[11px] uppercase tracking-widest " +
              (filter === t ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground hover:text-foreground")}
          >{t === "all" ? "All" : TYPE_LABEL[t]}</button>
        ))}
      </div>

      <div className="space-y-2">
        {filtered.length === 0 && (
          <div className="border border-border p-12 text-center text-muted-foreground text-sm">
            <Bell size={24} weight="bold" className="mx-auto mb-2 opacity-40" />
            No alerts in this category.
          </div>
        )}
        {filtered.map((a) => (
          <div key={a.id} data-testid={`alert-${a.id}`}
               className={"border-l-2 border bg-card p-4 flex gap-4 " + SEV_COLOR[a.severity]}>
            <Warning size={18} weight="bold" className="shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <div className="text-[10px] uppercase tracking-widest font-bold mono">
                  {TYPE_LABEL[a.type] || a.type}
                </div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground mono">
                  {a.severity}
                </div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground mono ml-auto">
                  {new Date(a.created_at).toUTCString().slice(5, 16)}
                </div>
              </div>
              <Link to={`/fund/${a.fund_id}`} className="text-foreground hover:text-primary block">
                <div className="text-base font-semibold mt-1">{a.title}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{a.fund_name}</div>
              </Link>
              <div className="text-sm mt-2 text-foreground/90">{a.message}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
