import { useEffect, useState } from "react";
import { api, fmtINR, fmtNum } from "../lib/api";
import { Calculator, ChartLineUp } from "@phosphor-icons/react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

export default function SipPlannerPage() {
  const [form, setForm] = useState({ monthly: 10000, years: 15, expected_return: 12, step_up: 10 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const calc = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/sip-planner", {
        monthly: parseFloat(form.monthly),
        years: parseInt(form.years),
        expected_return: parseFloat(form.expected_return),
        step_up: parseFloat(form.step_up),
      });
      setResult(data);
    } finally { setLoading(false); }
  };

  useEffect(() => { calc(); /* eslint-disable-next-line */ }, []);

  return (
    <div className="space-y-6" data-testid="sip-page">
      <div>
        <div className="label-uppercase">// Tools</div>
        <h1 className="text-3xl font-black tracking-tighter">SIP Planner</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-border">
        {/* Inputs */}
        <div className="bg-card p-5 lg:col-span-1">
          <div className="label-uppercase mb-4 flex items-center gap-2"><Calculator size={14} weight="bold" /> Parameters</div>
          <div className="space-y-4">
            {[
              { k: "monthly", label: "Monthly SIP (₹)", step: "100" },
              { k: "years", label: "Duration (Years)", step: "1" },
              { k: "expected_return", label: "Expected Return (%)", step: "0.1" },
              { k: "step_up", label: "Annual Step-up (%)", step: "0.5" },
            ].map((f) => (
              <div key={f.k}>
                <label className="label-uppercase block mb-1.5">{f.label}</label>
                <input
                  type="number" step={f.step} min="0"
                  data-testid={`sip-${f.k}`}
                  className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm mono focus:outline-none focus:border-primary"
                  value={form[f.k]}
                  onChange={(e) => setForm({ ...form, [f.k]: e.target.value })}
                />
              </div>
            ))}
            <button
              onClick={calc} disabled={loading}
              data-testid="sip-calc-btn"
              className="w-full bg-primary text-primary-foreground py-2.5 text-xs uppercase tracking-widest font-bold hover:bg-primary/90 disabled:opacity-60"
            >{loading ? "..." : "Calculate"}</button>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 bg-card p-5">
          {result && (
            <>
              <div className="grid grid-cols-3 gap-px bg-border">
                {[
                  ["Total Invested", fmtINR(result.summary.total_invested), ""],
                  ["Future Value", fmtINR(result.summary.future_value), "num-pos"],
                  ["Wealth Gain", fmtINR(result.summary.wealth_gain), "num-pos"],
                ].map(([k, v, c]) => (
                  <div key={k} className="bg-card p-4">
                    <div className="label-uppercase">{k}</div>
                    <div className={`mono text-xl mt-2 ${c}`}>{v}</div>
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <div className="label-uppercase mb-2 flex items-center gap-2"><ChartLineUp size={14} weight="bold" /> Year-by-year wealth</div>
                <div className="h-72">
                  <ResponsiveContainer>
                    <BarChart data={result.schedule}>
                      <CartesianGrid stroke="hsl(240 10% 15%)" vertical={false} />
                      <XAxis dataKey="year" stroke="hsl(240 5% 65%)" tick={{ fontSize: 11, fontFamily: "IBM Plex Mono" }} />
                      <YAxis stroke="hsl(240 5% 65%)" tick={{ fontSize: 11, fontFamily: "IBM Plex Mono" }}
                             tickFormatter={(v) => (v >= 1e7 ? (v/1e7).toFixed(1)+"Cr" : v >= 1e5 ? (v/1e5).toFixed(1)+"L" : v)} />
                      <Tooltip contentStyle={{ background: "hsl(240 10% 6%)", border: "1px solid hsl(240 10% 15%)", borderRadius: 0 }}
                               formatter={(v) => fmtNum(v, 0)} />
                      <Legend wrapperStyle={{ fontSize: 11, fontFamily: "IBM Plex Mono", textTransform: "uppercase", letterSpacing: 2 }} />
                      <Bar dataKey="invested" stackId="a" fill="hsl(240 5% 35%)" />
                      <Bar dataKey="wealth_gain" stackId="a" fill="hsl(142 71% 45%)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
