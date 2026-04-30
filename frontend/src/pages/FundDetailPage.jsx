import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, fmtNum, pct } from "../lib/api";
import {
  ArrowLeft, TrendUp, TrendDown, CheckCircle, XCircle, ArrowsLeftRight,
} from "@phosphor-icons/react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

const TABS = [
  { id: "performance", label: "Performance" },
  { id: "holdings", label: "Holdings Δ" },
  { id: "sectors", label: "Sectors Δ" },
  { id: "benchmark", label: "Benchmark" },
  { id: "news", label: "News" },
];

export default function FundDetailPage() {
  const { id } = useParams();
  const [tab, setTab] = useState("performance");
  const [fund, setFund] = useState(null);
  const [perf, setPerf] = useState(null);
  const [hdiff, setHdiff] = useState(null);
  const [sdiff, setSdiff] = useState(null);
  const [aa, setAa] = useState(null);
  const [news, setNews] = useState(null);

  useEffect(() => {
    api.get(`/funds/${id}`).then((r) => setFund(r.data));
    api.get(`/funds/${id}/performance`).then((r) => setPerf(r.data));
    api.get(`/funds/${id}/asset-allocation`).then((r) => setAa(r.data));
  }, [id]);

  useEffect(() => {
    if (tab === "holdings" && !hdiff) api.get(`/funds/${id}/holdings-diff`).then((r) => setHdiff(r.data));
    if (tab === "sectors" && !sdiff) api.get(`/funds/${id}/sector-diff`).then((r) => setSdiff(r.data));
    if (tab === "news" && !news) api.get(`/funds/${id}/news`).then((r) => setNews(r.data));
  }, [tab, id, hdiff, sdiff, news]);

  if (!fund) return <div className="label-uppercase">Loading...</div>;

  return (
    <div className="space-y-6" data-testid="fund-detail">
      <Link to="/" className="text-xs uppercase tracking-widest text-muted-foreground hover:text-primary inline-flex items-center gap-1" data-testid="back-link">
        <ArrowLeft size={12} weight="bold" /> Back
      </Link>

      {/* Header */}
      <div className="border border-border bg-card p-5">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <div className="label-uppercase">{fund.amc} · {fund.category}</div>
            <h1 className="text-2xl font-black tracking-tighter mt-1">{fund.name}</h1>
            <div className="text-xs text-muted-foreground mt-2 mono">
              Manager: <span className="text-foreground">{fund.manager}</span> ·
              Benchmark: <span className="text-foreground">{fund.benchmark}</span>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-px bg-border min-w-fit">
            {[
              ["NAV", fmtNum(fund.nav)],
              ["AUM (Cr)", fmtNum(fund.aum_cr, 0)],
              ["TER %", fmtNum(fund.expense_ratio)],
            ].map(([k, v]) => (
              <div key={k} className="bg-card px-4 py-2">
                <div className="label-uppercase">{k}</div>
                <div className="mono text-base mt-0.5">{v}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-px bg-border" data-testid="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            data-testid={`tab-${t.id}`}
            onClick={() => setTab(t.id)}
            className={"px-4 py-2 text-xs uppercase tracking-widest font-medium " +
              (tab === t.id ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground hover:text-foreground")}
          >{t.label}</button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "performance" && perf && (
        <div className="space-y-4" data-testid="perf-tab">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-px bg-border">
            {["1Y", "3Y", "5Y", "inception"].map((tf) => {
              const row = perf[tf];
              const beats = row.scheme >= row.benchmark;
              return (
                <div key={tf} className="bg-card p-4">
                  <div className="label-uppercase">{tf === "inception" ? "Inception" : tf}</div>
                  <div className="mono text-2xl mt-2">{pct(row.scheme)}</div>
                  <div className="text-[10px] uppercase tracking-widest text-muted-foreground mt-2">vs Cat {pct(row.category)}</div>
                  <div className={`text-[10px] uppercase tracking-widest mt-0.5 ${beats ? "num-pos" : "num-neg"}`}>
                    vs Bench {pct(row.benchmark)} · {beats ? "BEATS" : "TRAILS"}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-card border border-border p-4">
            <div className="label-uppercase mb-3">// Rolling 3Y returns — Scheme vs Benchmark</div>
            <div className="h-72">
              <ResponsiveContainer>
                <LineChart data={perf.rolling_3Y}>
                  <CartesianGrid stroke="hsl(240 10% 15%)" strokeDasharray="0" vertical={false} />
                  <XAxis dataKey="period" stroke="hsl(240 5% 65%)" tick={{ fontSize: 11, fontFamily: "IBM Plex Mono" }} />
                  <YAxis stroke="hsl(240 5% 65%)" tick={{ fontSize: 11, fontFamily: "IBM Plex Mono" }} unit="%" />
                  <Tooltip
                    contentStyle={{ background: "hsl(240 10% 6%)", border: "1px solid hsl(240 10% 15%)", borderRadius: 0 }}
                    labelStyle={{ color: "#fff", fontFamily: "Chivo" }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11, fontFamily: "IBM Plex Mono", textTransform: "uppercase", letterSpacing: 2 }} />
                  <Line type="linear" dataKey="scheme" stroke="hsl(142 71% 55%)" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="linear" dataKey="benchmark" stroke="hsl(43 100% 60%)" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {aa && (
            <div className="bg-card border border-border p-4">
              <div className="label-uppercase mb-3">// Asset Allocation Δ</div>
              <div className="grid grid-cols-3 gap-px bg-border">
                {["equity", "debt", "cash"].map((k) => {
                  const c = aa.current[k]; const p = aa.previous[k]; const d = +(c - p).toFixed(2);
                  return (
                    <div key={k} className="bg-card p-3">
                      <div className="label-uppercase">{k}</div>
                      <div className="mono text-lg mt-1">{fmtNum(c)}%</div>
                      <div className={"text-xs mono mt-1 " + (d > 0 ? "num-pos" : d < 0 ? "num-neg" : "text-muted-foreground")}>
                        prev {fmtNum(p)}% ({d >= 0 ? "+" : ""}{fmtNum(d)})
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "holdings" && hdiff && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-border" data-testid="holdings-tab">
          {[
            { key: "new_buys", label: "New Buys", icon: TrendUp, color: "num-pos" },
            { key: "exits", label: "Exits", icon: XCircle, color: "num-neg" },
            { key: "increased", label: "Increased Weight", icon: TrendUp, color: "num-pos" },
            { key: "decreased", label: "Decreased Weight", icon: TrendDown, color: "num-neg" },
          ].map((b) => (
            <div key={b.key} className="bg-card p-4">
              <div className="label-uppercase flex items-center gap-2 mb-3">
                <b.icon size={12} weight="bold" /> {b.label} ({hdiff.diff[b.key].length})
              </div>
              <div className="space-y-1.5">
                {hdiff.diff[b.key].length === 0 && <div className="text-xs text-muted-foreground">— None —</div>}
                {hdiff.diff[b.key].map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-xs mono border-b border-border/40 py-1.5">
                    <div>
                      <div className="font-sans text-sm">{s.stock}</div>
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{s.sector}</div>
                    </div>
                    <div className="text-right">
                      <div>{fmtNum(s.weight)}%</div>
                      <div className={b.color}>{s.delta >= 0 ? "+" : ""}{fmtNum(s.delta)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "sectors" && sdiff && (
        <div className="bg-card border border-border p-5" data-testid="sectors-tab">
          <div className="label-uppercase mb-4 flex items-center gap-2"><ArrowsLeftRight size={14} weight="bold" /> Sector Allocation Month-on-Month</div>
          <div className="space-y-3">
            {sdiff.rows.map((r) => {
              const max = Math.max(r.current, r.previous, 1);
              return (
                <div key={r.sector} className="grid grid-cols-12 items-center gap-3" data-testid={`sector-${r.sector}`}>
                  <div className="col-span-3 text-sm font-medium">{r.sector}</div>
                  <div className="col-span-7">
                    <div className="flex h-6 bg-muted/40">
                      <div className="bg-muted-foreground/50" style={{ width: `${(r.previous / max) * 100}%` }} />
                    </div>
                    <div className="flex h-6 mt-1 bg-muted/40">
                      <div className={r.delta >= 0 ? "bg-primary" : "bg-destructive"} style={{ width: `${(r.current / max) * 100}%` }} />
                    </div>
                  </div>
                  <div className="col-span-2 mono text-xs text-right">
                    <div>{fmtNum(r.current)}% <span className="text-muted-foreground">/ {fmtNum(r.previous)}%</span></div>
                    <div className={"text-[11px] " + (r.delta >= 0 ? "num-pos" : "num-neg") + (r.flag ? " font-bold" : "")}>
                      {r.delta >= 0 ? "+" : ""}{fmtNum(r.delta)}{r.flag ? " ⚑" : ""}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 text-[11px] text-muted-foreground">⚑ Flagged: |Δ| ≥ 2.00%</div>
        </div>
      )}

      {tab === "benchmark" && perf && (
        <div className="bg-card border border-border p-5" data-testid="benchmark-tab">
          <div className="label-uppercase mb-4">// Benchmark Beating History</div>
          <div className="grid grid-cols-3 gap-px bg-border">
            {["5Y", "10Y", "15Y"].map((p) => {
              const beats = perf.benchmark_history[p];
              const diff = perf.differentials[p];
              return (
                <div key={p} className="bg-card p-5">
                  <div className="label-uppercase">{p} Period</div>
                  <div className="mt-3 flex items-center gap-2">
                    {beats ? <CheckCircle size={20} weight="fill" className="text-primary" /> :
                      <XCircle size={20} weight="fill" className="text-destructive" />}
                    <div className={"font-black tracking-tight text-xl " + (beats ? "num-pos" : "num-neg")}>
                      {beats ? "BEATS" : "TRAILS"}
                    </div>
                  </div>
                  <div className="mt-3 mono text-xs text-muted-foreground">Differential</div>
                  <div className={"mono text-2xl " + (diff >= 0 ? "num-pos" : "num-neg")}>
                    {diff >= 0 ? "+" : ""}{fmtNum(diff)}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {tab === "news" && (
        <div className="bg-card border border-border p-5" data-testid="news-tab">
          <div className="label-uppercase mb-4">// News Wire — {fund.amc}</div>
          {!news ? <div className="text-xs text-muted-foreground">Fetching wire...</div> :
            news.items.length === 0 ? <div className="text-xs text-muted-foreground">No items found.</div> :
              <div className="space-y-3">
                {news.items.map((n, i) => (
                  <a key={i} href={n.link} target="_blank" rel="noreferrer"
                     data-testid={`news-${i}`}
                     className="block border border-border p-3 hover:border-primary transition-colors">
                    <div className="text-sm font-medium leading-snug" dangerouslySetInnerHTML={{ __html: n.title }} />
                    <div className="text-[10px] uppercase tracking-widest text-muted-foreground mt-1.5 mono">
                      {n.published}
                    </div>
                  </a>
                ))}
              </div>}
        </div>
      )}
    </div>
  );
}
