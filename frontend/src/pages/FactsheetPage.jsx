import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { UploadSimple, FileText, Sparkle, CheckCircle, Warning } from "@phosphor-icons/react";

export default function FactsheetPage() {
  const [funds, setFunds] = useState([]);
  const [fundId, setFundId] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => { api.get("/funds").then((r) => setFunds(r.data)); }, []);

  useEffect(() => {
    if (!fundId) return setHistory([]);
    api.get(`/funds/${fundId}/factsheets`).then((r) => setHistory(r.data));
  }, [fundId]);

  const upload = async (e) => {
    e.preventDefault();
    setErr(""); setResult(null);
    if (!fundId || !file) { setErr("Select a fund and a PDF."); return; }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post(`/funds/${fundId}/factsheet`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data);
      const r = await api.get(`/funds/${fundId}/factsheets`);
      setHistory(r.data);
    } catch (e2) {
      setErr(e2.response?.data?.detail || e2.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="factsheet-page">
      <div>
        <div className="label-uppercase">// Tools</div>
        <h1 className="text-3xl font-black tracking-tighter">Factsheet Ingestion</h1>
        <div className="text-xs text-muted-foreground mt-2 max-w-2xl">
          Upload a monthly factsheet PDF — Gemini extracts holdings, sectors, manager, AUM and stores a snapshot.
          When the new snapshot differs from the previous one (manager / category / objective / asset-allocation),
          alerts are auto-created and emailed to opted-in holders.
        </div>
      </div>

      <form onSubmit={upload} className="bg-card border border-border p-5 space-y-4">
        <div>
          <label className="label-uppercase block mb-1.5">Fund</label>
          <select
            data-testid="fs-fund-select"
            className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm focus:outline-none focus:border-primary"
            value={fundId} onChange={(e) => setFundId(e.target.value)} required
          >
            <option value="">Select a fund...</option>
            {funds.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label-uppercase block mb-1.5">Factsheet PDF</label>
          <label className="block border-2 border-dashed border-border bg-secondary/20 p-6 text-center cursor-pointer hover:border-primary"
                 data-testid="fs-drop">
            <input type="file" accept="application/pdf" className="hidden"
                   data-testid="fs-file-input"
                   onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <UploadSimple size={24} weight="bold" className="mx-auto mb-2 text-muted-foreground" />
            <div className="text-sm">{file ? file.name : "Click or drop a PDF here"}</div>
            <div className="text-[11px] text-muted-foreground mt-1">Max 15 MB · PDF only</div>
          </label>
        </div>

        {err && <div className="text-xs text-destructive border border-destructive/40 bg-destructive/5 px-3 py-2">{err}</div>}

        <button
          type="submit" disabled={busy}
          data-testid="fs-upload-btn"
          className="bg-primary text-primary-foreground px-5 py-2.5 text-xs uppercase tracking-widest font-bold hover:bg-primary/90 disabled:opacity-60 flex items-center gap-2"
        >
          <Sparkle size={14} weight="bold" />
          {busy ? "Extracting via Gemini..." : "Upload & Extract"}
        </button>
      </form>

      {result && (
        <div className="space-y-4" data-testid="fs-result">
          <div className="bg-card border border-border p-5">
            <div className="label-uppercase mb-3 flex items-center gap-2">
              <CheckCircle size={14} weight="bold" className="text-primary" /> Extracted snapshot
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border">
              {[
                ["Fund", result.extracted?.fund_name?.slice(0, 26) || "—"],
                ["Manager", result.extracted?.manager?.slice(0, 26) || "—"],
                ["Category", result.extracted?.category || "—"],
                ["AUM (Cr)", result.extracted?.aum_cr ?? "—"],
              ].map(([k, v]) => (
                <div key={k} className="bg-card p-3">
                  <div className="label-uppercase">{k}</div>
                  <div className="mono text-sm mt-1.5">{v}</div>
                </div>
              ))}
            </div>
            {result.extracted?.top_holdings?.length > 0 && (
              <div className="mt-4">
                <div className="label-uppercase mb-2">Top holdings ({result.extracted.top_holdings.length})</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-xs mono">
                  {result.extracted.top_holdings.slice(0, 10).map((h, i) => (
                    <div key={i} className="flex justify-between border-b border-border/40 py-1.5">
                      <span className="font-sans text-sm">{h.stock}</span>
                      <span>{h.weight}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {result.alerts_generated?.length > 0 && (
            <div className="bg-card border border-destructive/40 p-5">
              <div className="label-uppercase mb-3 flex items-center gap-2 text-destructive">
                <Warning size={14} weight="bold" /> {result.alerts_generated.length} change(s) detected
              </div>
              <div className="space-y-2">
                {result.alerts_generated.map((a, i) => (
                  <div key={i} className="border-l-2 border-destructive bg-destructive/5 p-3" data-testid={`fs-alert-${i}`}>
                    <div className="text-[10px] uppercase tracking-widest text-destructive mono">{a.type.replace(/_/g, " ")}</div>
                    <div className="text-sm font-semibold mt-1">{a.title}</div>
                    <div className="text-xs text-foreground/80 mt-1">{a.message}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!result.had_previous_snapshot && (
            <div className="text-xs text-muted-foreground border border-border bg-secondary/30 p-3">
              First snapshot for this fund — no diff to compare against. Upload another factsheet later to detect changes.
            </div>
          )}
        </div>
      )}

      {fundId && history.length > 0 && (
        <div className="bg-card border border-border" data-testid="fs-history">
          <div className="label-uppercase p-4 border-b border-border flex items-center gap-2"><FileText size={14} weight="bold" /> Snapshot history</div>
          <table className="w-full text-xs mono">
            <thead>
              <tr className="border-b border-border text-muted-foreground uppercase">
                <th className="text-left py-2.5 px-4 font-medium">Uploaded</th>
                <th className="text-left py-2.5 px-4 font-medium">File</th>
                <th className="text-left py-2.5 px-4 font-medium">Manager</th>
                <th className="text-right py-2.5 px-4 font-medium">Holdings</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className="border-b border-border/40">
                  <td className="py-2.5 px-4">{new Date(h.created_at).toUTCString().slice(5, 22)}</td>
                  <td className="py-2.5 px-4">{h.filename}</td>
                  <td className="py-2.5 px-4">{(h.extracted?.manager || "—").slice(0, 30)}</td>
                  <td className="text-right py-2.5 px-4">{h.extracted?.top_holdings?.length || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
