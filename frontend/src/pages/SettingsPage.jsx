import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Bell, EnvelopeSimple, CheckCircle, WarningCircle, PaperPlaneTilt } from "@phosphor-icons/react";

export default function SettingsPage() {
  const [s, setS] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => { api.get("/settings/notifications").then((r) => setS(r.data)); }, []);

  const save = async () => {
    setSaving(true); setMsg(null);
    try {
      const { data } = await api.put("/settings/notifications", {
        notify_realtime: s.notify_realtime,
        notify_digest: s.notify_digest,
        notification_email: s.notification_email,
      });
      setS({ ...s, ...data });
      setMsg({ type: "ok", text: "Settings saved." });
    } catch (e) {
      setMsg({ type: "err", text: e.response?.data?.detail || e.message });
    } finally { setSaving(false); }
  };

  const sendTest = async () => {
    setMsg(null);
    try {
      const { data } = await api.post("/notifications/test");
      setMsg({ type: "ok", text: `Test email sent to ${data.sent_to} (id: ${data.id?.slice(0, 8)}…)` });
    } catch (e) {
      setMsg({ type: "err", text: e.response?.data?.detail || e.message });
    }
  };

  const sendDigest = async () => {
    setMsg(null);
    try {
      const { data } = await api.post("/notifications/digest");
      setMsg({ type: "ok", text: `Digest of ${data.alert_count} signals sent to ${data.sent_to}.` });
    } catch (e) {
      setMsg({ type: "err", text: e.response?.data?.detail || e.message });
    }
  };

  if (!s) return <div className="label-uppercase">Loading...</div>;

  return (
    <div className="space-y-6 max-w-2xl" data-testid="settings-page">
      <div>
        <div className="label-uppercase">// Settings</div>
        <h1 className="text-3xl font-black tracking-tighter">Notification Preferences</h1>
      </div>

      <div className="bg-card border border-border p-5 space-y-5">
        <div>
          <label className="label-uppercase block mb-1.5 flex items-center gap-2">
            <EnvelopeSimple size={12} weight="bold" /> Notification Email
          </label>
          <input
            data-testid="notif-email"
            type="email"
            className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm mono focus:outline-none focus:border-primary"
            value={s.notification_email || ""}
            onChange={(e) => setS({ ...s, notification_email: e.target.value })}
          />
          <div className="text-[11px] text-muted-foreground mt-1.5">
            Account email: <span className="mono">{s.email}</span>. Resend free tier requires this to be the verified
            owner address until you connect a custom domain.
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-border">
          {[
            { k: "notify_realtime", label: "Real-time per alert", sub: "Every new signal triggers an email" },
            { k: "notify_digest", label: "On-demand digest", sub: "Manual digest via the button below" },
          ].map((row) => (
            <button
              key={row.k}
              data-testid={`toggle-${row.k}`}
              onClick={() => setS({ ...s, [row.k]: !s[row.k] })}
              className={"bg-card p-4 text-left border-l-2 " + (s[row.k] ? "border-l-primary" : "border-l-transparent")}
            >
              <div className="flex items-center justify-between">
                <div className="label-uppercase">{row.label}</div>
                <div className={"w-10 h-5 border border-border relative " + (s[row.k] ? "bg-primary" : "bg-secondary")}>
                  <div className={"absolute top-0.5 w-4 h-4 bg-foreground transition-all " + (s[row.k] ? "left-5" : "left-0.5")} />
                </div>
              </div>
              <div className="text-xs text-muted-foreground mt-2">{row.sub}</div>
            </button>
          ))}
        </div>

        {msg && (
          <div className={"text-xs px-3 py-2 border flex items-start gap-2 " +
            (msg.type === "ok" ? "border-primary/40 bg-primary/5 text-primary" : "border-destructive/40 bg-destructive/5 text-destructive")}>
            {msg.type === "ok" ? <CheckCircle size={14} weight="bold" /> : <WarningCircle size={14} weight="bold" />}
            <span>{msg.text}</span>
          </div>
        )}

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            onClick={save} disabled={saving}
            data-testid="save-settings"
            className="bg-primary text-primary-foreground px-4 py-2 text-xs uppercase tracking-widest font-bold hover:bg-primary/90 disabled:opacity-60"
          >{saving ? "..." : "Save"}</button>
          <button
            onClick={sendTest}
            data-testid="send-test"
            className="border border-border px-4 py-2 text-xs uppercase tracking-widest hover:bg-secondary flex items-center gap-2"
          ><Bell size={12} weight="bold" /> Send test email</button>
          <button
            onClick={sendDigest}
            data-testid="send-digest"
            className="border border-border px-4 py-2 text-xs uppercase tracking-widest hover:bg-secondary flex items-center gap-2"
          ><PaperPlaneTilt size={12} weight="bold" /> Send digest now</button>
        </div>
      </div>
    </div>
  );
}
