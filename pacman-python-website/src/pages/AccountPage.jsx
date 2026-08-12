import { useState } from "react";
import { post } from "../api/client";

export function AccountPage({ onUser }) {
  const [message, setMessage] = useState("");
  const change = async (event) => { event.preventDefault(); try { const body = Object.fromEntries(new FormData(event.currentTarget)); const data = await post("/api/auth/change-password", body); onUser(data.user); event.currentTarget.reset(); setMessage("Password changed."); } catch (e) { setMessage(e.message); } };
  const logout = async () => { await post("/api/auth/logout", {}); onUser(null); };
  return <div className="center-card surface account-page"><h2>Account</h2><form className="form-stack" onSubmit={change}><label>Current password<input name="old_password" type="password" required /></label><label>New password<input name="new_password" type="password" minLength="6" required /></label><button className="primary">Change password</button></form>{message && <div className="notice">{message}</div>}<button onClick={logout}>Logout</button></div>;
}
