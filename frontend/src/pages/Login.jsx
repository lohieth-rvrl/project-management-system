import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api.js";

export default function Login() {
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
      nav("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card login" onSubmit={submit}>
      <h1>Project Management System</h1>
      <p className="sub">Sign in to continue</p>
      <label>Username</label>
      <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
      <div style={{ height: 12 }} />
      <label>Password</label>
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      {error && <div className="error">{error}</div>}
      <div style={{ height: 16 }} />
      <button disabled={busy} style={{ width: "100%" }}>{busy ? "Signing in..." : "Sign in"}</button>
    </form>
  );
}
