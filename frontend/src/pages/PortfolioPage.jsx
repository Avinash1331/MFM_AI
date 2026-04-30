import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtINR, fmtNum, pct } from "../lib/api";
import { usePortfolio } from "../lib/portfolio.jsx";
import { Plus, Trash, X } from "@phosphor-icons/react";

export default function PortfolioPage() {
  const { activeId } = usePortfolio() || {};
  const [portfolio, setPortfolio] = useState(null);
  const [funds, setFunds] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ fund_id: "", units: "", avg_cost: "", purchase_date: "" });
  const [err, setErr] = useState("");

  const load = async () => {
    if (!activeId) return;
    const [p, f] = await Promise.all([
      api.get("/portfolio", { params: { portfolio_id: activeId } }),
      api.get("/funds"),
    ]);
    setPortfolio(p.data); setFunds(f.data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [activeId]);

  const addItem = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.post("/portfolio", {
        fund_id: form.fund_id,
        units: parseFloat(form.units),
        avg_cost: parseFloat(form.avg_cost),
        portfolio_id: activeId,
        purchase_date: form.purchase_date
          ? new Date(form.purchase_date).toISOString()
          : undefined,
      });
      setShowAdd(false);
      setForm({ fund_id: "", units: "", avg_cost: "", purchase_date: "" });
      load();
    } catch (e2) {
      setErr(e2.response?.data?.detail || e2.message);
    }
  };

  const remove = async (id) => {
    await api.delete(`/portfolio/${id}`);
    load();
  };

  if (!portfolio) return <div className="label-uppercase">Loading...</div>;

  return (
    <div className="space-y-6" data-testid="portfolio-page">
      <div className="flex items-baseline justify-between">
        <div>
          <div className="label-uppercase">// Portfolio</div>
          <h1 className="text-3xl font-black tracking-tighter">Holdings Manager</h1>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          data-testid="add-fund-btn"
          className="bg-primary text-primary-foreground px-4 py-2 text-xs uppercase tracking-widest flex items-center gap-2 hover:bg-primary/90"
        >
          <Plus size={14} weight="bold" /> Add Scheme
        </button>
      </div>

      <div className="bg-card border border-border">
        <table className="w-full text-xs mono">
          <thead>
            <tr className="border-b border-border text-muted-foreground uppercase">
              <th className="text-left py-3 px-4 font-medium">Scheme</th>
              <th className="text-right py-3 px-4 font-medium">Units</th>
              <th className="text-right py-3 px-4 font-medium">Avg Cost</th>
              <th className="text-right py-3 px-4 font-medium">NAV</th>
              <th className="text-right py-3 px-4 font-medium">Invested</th>
              <th className="text-right py-3 px-4 font-medium">Value</th>
              <th className="text-right py-3 px-4 font-medium">P&amp;L %</th>
              <th className="py-3 px-4"></th>
            </tr>
          </thead>
          <tbody>
            {portfolio.holdings.map((h) => (
              <tr key={h.id} className="border-b border-border/50 hover:bg-secondary/30">
                <td className="py-3 px-4">
                  <Link to={`/fund/${h.fund_id}`} className="hover:text-primary" data-testid={`pf-row-${h.fund_id}`}>
                    <div className="font-sans text-sm font-medium">{h.fund.name}</div>
                    <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{h.fund.category}</div>
                  </Link>
                </td>
                <td className="text-right py-3 px-4">{fmtNum(h.units)}</td>
                <td className="text-right py-3 px-4">{fmtNum(h.avg_cost)}</td>
                <td className="text-right py-3 px-4">{fmtNum(h.fund.nav)}</td>
                <td className="text-right py-3 px-4">{fmtINR(h.invested)}</td>
                <td className="text-right py-3 px-4">{fmtINR(h.current_value)}</td>
                <td className={`text-right py-3 px-4 ${h.gain_pct >= 0 ? "num-pos" : "num-neg"}`}>{pct(h.gain_pct)}</td>
                <td className="text-right py-3 px-4">
                  <button
                    onClick={() => remove(h.id)}
                    data-testid={`remove-${h.id}`}
                    className="text-muted-foreground hover:text-destructive"
                  ><Trash size={14} /></button>
                </td>
              </tr>
            ))}
            {portfolio.holdings.length === 0 && (
              <tr><td colSpan={8} className="py-12 text-center text-muted-foreground">No holdings. Click <span className="text-primary">Add Scheme</span> to start.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50" data-testid="add-modal">
          <div className="bg-card border border-border max-w-md w-full">
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <div className="label-uppercase">// Add Scheme</div>
              <button onClick={() => setShowAdd(false)} data-testid="close-modal"><X size={16} /></button>
            </div>
            <form onSubmit={addItem} className="p-5 space-y-4">
              <div>
                <label className="label-uppercase block mb-1.5">Scheme</label>
                <select
                  data-testid="fund-select"
                  className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm focus:outline-none focus:border-primary"
                  value={form.fund_id}
                  onChange={(e) => setForm({ ...form, fund_id: e.target.value })}
                  required
                >
                  <option value="">Select a fund...</option>
                  {funds.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label-uppercase block mb-1.5">Units</label>
                  <input
                    data-testid="units-input"
                    type="number" step="0.001" min="0.001" required
                    className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm mono focus:outline-none focus:border-primary"
                    value={form.units}
                    onChange={(e) => setForm({ ...form, units: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label-uppercase block mb-1.5">Avg cost</label>
                  <input
                    data-testid="cost-input"
                    type="number" step="0.01" min="0.01" required
                    className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm mono focus:outline-none focus:border-primary"
                    value={form.avg_cost}
                    onChange={(e) => setForm({ ...form, avg_cost: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <label className="label-uppercase block mb-1.5">Purchase Date (optional)</label>
                <input
                  data-testid="date-input"
                  type="date"
                  className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm mono focus:outline-none focus:border-primary"
                  value={form.purchase_date}
                  onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
                />
                <div className="text-[10px] text-muted-foreground mt-1">Used for STCG/LTCG classification.</div>
              </div>
              {err && <div className="text-xs text-destructive">{err}</div>}
              <button
                data-testid="add-submit"
                className="w-full bg-primary text-primary-foreground py-2.5 text-xs uppercase tracking-widest font-bold hover:bg-primary/90"
              >Add to portfolio</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
