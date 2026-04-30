import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth.jsx";
import { Pulse, ArrowRight } from "@phosphor-icons/react";

export default function LoginPage({ mode = "login" }) {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState(mode === "login" ? "admin@mfintel.com" : "");
  const [password, setPassword] = useState(mode === "login" ? "Admin@12345" : "");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    const result = mode === "login"
      ? await login(email, password)
      : await register(email, password, name || "Investor");
    setLoading(false);
    if (result.ok) nav("/", { replace: true });
    else setErr(result.error || "Unknown error");
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background text-foreground">
      {/* Left: form */}
      <div className="flex flex-col justify-center px-8 sm:px-16 py-10 border-r border-border">
        <div className="max-w-md w-full mx-auto">
          <div className="flex items-center gap-2 mb-12">
            <Pulse size={20} weight="bold" className="text-primary" />
            <div className="font-black tracking-tighter">MF.TERMINAL</div>
          </div>

          <div className="label-uppercase mb-2">// {mode === "login" ? "Authenticate" : "Open Terminal"}</div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tighter mb-2">
            {mode === "login" ? "Access your portfolio." : "Create an account."}
          </h1>
          <p className="text-sm text-muted-foreground mb-8">
            {mode === "login"
              ? "Real-time intelligence for the informed investor."
              : "Track holdings, flag changes, and stay ahead of every AMC move."}
          </p>

          <form onSubmit={submit} className="space-y-4" data-testid={`${mode}-form`}>
            {mode === "register" && (
              <div>
                <label className="label-uppercase block mb-1.5">Name</label>
                <input
                  data-testid="name-input"
                  className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm focus:outline-none focus:border-primary"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            )}
            <div>
              <label className="label-uppercase block mb-1.5">Email</label>
              <input
                data-testid="email-input"
                type="email"
                className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm mono focus:outline-none focus:border-primary"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label-uppercase block mb-1.5">Password</label>
              <input
                data-testid="password-input"
                type="password"
                className="w-full bg-secondary/50 border border-border px-3 py-2.5 text-sm mono focus:outline-none focus:border-primary"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={6}
                required
              />
            </div>

            {err && (
              <div data-testid="auth-error" className="text-xs text-destructive border border-destructive/40 bg-destructive/10 px-3 py-2">
                {err}
              </div>
            )}

            <button
              data-testid="submit-btn"
              disabled={loading}
              className="w-full bg-primary text-primary-foreground font-bold py-3 text-sm uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-60"
            >
              {loading ? "..." : mode === "login" ? "Sign in" : "Create account"}
              <ArrowRight size={14} weight="bold" />
            </button>
          </form>

          <div className="mt-6 text-xs text-muted-foreground">
            {mode === "login" ? (
              <>No account? <Link to="/register" data-testid="link-register" className="text-primary hover:underline">Register →</Link></>
            ) : (
              <>Already onboard? <Link to="/login" data-testid="link-login" className="text-primary hover:underline">Sign in →</Link></>
            )}
          </div>
          {mode === "login" && (
            <div className="mt-8 border border-border p-3 text-xs">
              <div className="label-uppercase mb-1">Demo creds</div>
              <div className="mono">admin@mfintel.com</div>
              <div className="mono">Admin@12345</div>
            </div>
          )}
        </div>
      </div>

      {/* Right: hero */}
      <div className="hidden lg:block relative overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center opacity-20"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1775057154553-0f3e8902fea3?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600')",
          }}
        />
        <div className="absolute inset-0 grid-bg opacity-40" />
        <div className="absolute inset-0 scanline" />
        <div className="relative h-full flex flex-col justify-end p-12">
          <div className="label-uppercase text-primary mb-4">// Live since 2026</div>
          <div className="font-black text-5xl tracking-tighter leading-none mb-6">
            Watch every<br />holding move.
          </div>
          <div className="grid grid-cols-3 gap-px bg-border mt-6 max-w-md">
            {[
              ["1Y", "+24.8%", "num-pos"],
              ["3Y", "+19.2%", "num-pos"],
              ["5Y", "+22.1%", "num-pos"],
            ].map(([k, v, c]) => (
              <div key={k} className="bg-card p-4">
                <div className="label-uppercase">{k}</div>
                <div className={`mono text-lg ${c}`}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
