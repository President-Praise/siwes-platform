import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export function Login() {
  const { refresh } = useAuth();
  const [username, setUsername] = useState("superadmin");
  const [pin, setPin] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      await api.login(username.trim().toLowerCase(), pin);
      await refresh();
    } catch (e: any) {
      setErr(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <div>
          <h1 className="text-xl font-head font-bold text-navy">SIWES Platform Admin</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to manage schools and orders.</p>
        </div>
        <div>
          <label className="label">Username</label>
          <input
            className="input"
            value={username}
            onChange={e => setUsername(e.target.value)}
            placeholder="superadmin or your username"
            autoFocus
          />
        </div>
        <div>
          <label className="label">PIN</label>
          <input
            className="input"
            type="password"
            value={pin}
            onChange={e => setPin(e.target.value)}
            placeholder="••••"
          />
        </div>
        {err && <div className="text-red-600 text-sm">{err}</div>}
        <button className="btn btn-primary w-full" type="submit" disabled={loading || pin.length < 4}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
