import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api.js";

export default function Account() {
  const { me } = useOutletContext();
  const qc = useQueryClient();
  const toggleEmail = async (e) => {
    await api("/users/me/", { method: "PATCH", body: { email_notifications: e.target.checked } });
    qc.invalidateQueries({ queryKey: ["me"] });
  };
  const [form, setForm] = useState({ old_password: "", new_password: "", confirm: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => { setForm({ ...form, [k]: e.target.value }); setDone(false); };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.new_password !== form.confirm) { setError("New passwords do not match"); return; }
    setBusy(true);
    try {
      await api("/users/change-password/", {
        method: "POST", body: { old_password: form.old_password, new_password: form.new_password },
      });
      setDone(true);
      setForm({ old_password: "", new_password: "", confirm: "" });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1>My account</h1>
      <div className="sub">Change your password. Use at least 8 characters that are not a common password.</div>
      <div className="card" style={{ maxWidth: 420, marginBottom: 12 }}>
        <label><input type="checkbox" checked={me?.email_notifications ?? true} onChange={toggleEmail} /> Email me about my notifications</label>
      </div>
      <form className="card stack" style={{ maxWidth: 420 }} onSubmit={submit}>
        <div><label>Current password</label>
          <input type="password" value={form.old_password} onChange={set("old_password")} required autoComplete="current-password" /></div>
        <div><label>New password</label>
          <input type="password" value={form.new_password} onChange={set("new_password")} required minLength={8} autoComplete="new-password" /></div>
        <div><label>Confirm new password</label>
          <input type="password" value={form.confirm} onChange={set("confirm")} required autoComplete="new-password" /></div>
        {error && <div className="error">{error}</div>}
        {done && <div style={{ color: "var(--ok)" }}>Password changed.</div>}
        <button disabled={busy}>{busy ? "Saving..." : "Change password"}</button>
      </form>
    </>
  );
}
