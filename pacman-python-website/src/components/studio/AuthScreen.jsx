import { useState } from "react";
import { post } from "../../api/client";

export function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); const values = Object.fromEntries(new FormData(event.currentTarget));
    try { const data = await post(`/api/auth/${mode}`, values); onAuthenticated(data.user); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  return <main className="auth-screen"><section className="auth-card">
    <div className="brand"><span className="brand-mark">A1</span><div><h1>AIP1 Studio</h1><p>Python learning fundamentals</p></div></div>
    <div className="auth-switch"><button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Login</button><button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Create student</button></div>
    <form className="form-stack" onSubmit={submit}>
      {mode === "register" && <label>Name<input name="display_name" required /></label>}
      <label>Username<input name="username" autoComplete="username" required /></label>
      <label>Password<input name="password" type="password" minLength="6" autoComplete={mode === "login" ? "current-password" : "new-password"} required /></label>
      {error && <p className="error-banner">{error}</p>}<button className="primary" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Login" : "Create account"}</button>
    </form>
  </section></main>;
}
