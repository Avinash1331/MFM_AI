import { useEffect, useState } from "react";
import { api, fmtINR } from "../lib/api";
import { Receipt, Info } from "@phosphor-icons/react";

export default function TaxReportPage() {
  const [portfolios, setPortfolios] = useState([]);
  const [pid, setPid] = useState(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/portfolios").then((r) => {
      setPortfolios(r.data);
      if (r.data.length) setPid(r.data[0].id);
    });
  }, []);

  useEffect(() => {
    if (!pid) return;
    setData(null);
    api.get(`/portfolios/${pid}/tax-report`).then((r) => setData(r.data));
  }, [pid]);

  return (
    <div className="space-y-6" data-testid="tax-page">
      <div className="flex items-baseline justify-between flex-wrap gap-4">
        <div>
          <div className="label-uppercase">// Tools</div>
          <h1 className="text-3xl font-black tracking-tighter">Capital Gains Estimator</h1>
        </div>
        <select
          data-testid="tax-portfolio-select"
          className="bg-secondary/50 border border-border px-3 py-2 text-xs uppercase tracking-widest"
          value={pid || ""} onChange={(e) => setPid(e.target.value)}
        >
          {portfolios.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {!data ? <div className="label-uppercase">Loading...</div> : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border">
            {[
              ["STCG Gain", fmtINR(data.summary.stcg_gain), data.summary.stcg_gain >= 0 ? "num-pos" : "num-neg"],
              ["LTCG Gain", fmtINR(data.summary.ltcg_gain), data.summary.ltcg_gain >= 0 ? "num-pos" : "num-neg"],
              ["LTCG Taxable", fmtINR(data.summary.ltcg_taxable), "text-accent"],
              ["Estimated Tax", fmtINR(data.summary.total_estimated_tax), "num-neg"],
            ].map(([k, v, c]) => (
              <div key={k} className="bg-card p-4">
                <div className="label-uppercase">{k}</div>
                <div className={`mono text-xl mt-2 ${c}`}>{v}</div>
              </div>
            ))}
          </div>

          <div className="bg-card border border-border p-4 text-xs flex items-start gap-3">
            <Info size={16} weight="bold" className="text-accent shrink-0 mt-0.5" />
            <div>
              <div className="font-medium">Indian equity-MF rules applied</div>
              <div className="text-muted-foreground mt-1">
                STCG (≤1Y) @ 15% · LTCG (>1Y) @ 10% above ₹{fmtINR(data.summary.ltcg_exemption)} exemption per FY ·
                {" "}Estimates only — confirm with your CA. Indexation not applied.
              </div>
            </div>
          </div>

          <div className="bg-card border border-border">
            <div className="label-uppercase p-4 border-b border-border flex items-center gap-2">
              <Receipt size={14} weight="bold" /> Lot-level View
            </div>
            <table className="w-full text-xs mono">
              <thead>
                <tr className="border-b border-border text-muted-foreground uppercase">
                  <th className="text-left py-3 px-4 font-medium">Scheme</th>
                  <th className="text-left py-3 px-4 font-medium">Purchase</th>
                  <th className="text-right py-3 px-4 font-medium">Days</th>
                  <th className="text-right py-3 px-4 font-medium">Term</th>
                  <th className="text-right py-3 px-4 font-medium">Invested</th>
                  <th className="text-right py-3 px-4 font-medium">Value</th>
                  <th className="text-right py-3 px-4 font-medium">Gain</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.id} className="border-b border-border/50">
                    <td className="py-3 px-4 font-sans text-sm">{r.fund_name}</td>
                    <td className="py-3 px-4">{r.purchase_date}</td>
                    <td className="text-right py-3 px-4">{r.days_held}</td>
                    <td className={"text-right py-3 px-4 " + (r.term === "LTCG" ? "num-pos" : "text-accent")}>{r.term}</td>
                    <td className="text-right py-3 px-4">{fmtINR(r.invested)}</td>
                    <td className="text-right py-3 px-4">{fmtINR(r.current_value)}</td>
                    <td className={"text-right py-3 px-4 " + (r.gain >= 0 ? "num-pos" : "num-neg")}>{fmtINR(r.gain)}</td>
                  </tr>
                ))}
                {data.rows.length === 0 && (
                  <tr><td colSpan={7} className="py-8 text-center text-muted-foreground">No holdings in this portfolio.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
