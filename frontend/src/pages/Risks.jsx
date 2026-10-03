import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOutletContext } from "react-router-dom";
import { api, list } from "../api.js";
import Badge from "../components/Badge.jsx";

export default function Risks() {
  const { me } = useOutletContext();
  const qc = useQueryClient();
  const [form, setForm] = useState({ project: "", title: "", probability: 3, impact: 3, mitigation: "" });
  const [error, setError] = useState("");

  const { data: risks = [] } = useQuery({ queryKey: ["risks"], queryFn: () => list("/risks/") });
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: () => list("/projects/") });
  const code = (id) => projects.find((p) => p.id === id)?.code || id;
  const canWrite = me && me.role !== "viewer";

  const refresh = () => { qc.invalidateQueries({ queryKey: ["risks"] }); qc.invalidateQueries({ queryKey: ["overview"] }); };
  const add = useMutation({
    mutationFn: (b) => api("/risks/", { method: "POST", body: { ...b, owner: me.id } }),
    onSuccess: () => { refresh(); setForm({ ...form, title: "", mitigation: "" }); setError(""); },
    onError: (e) => setError(e.message),
  });
  const setStatus = useMutation({
    mutationFn: ({ id, status }) => api(`/risks/${id}/`, { method: "PATCH", body: { status } }),
    onSuccess: refresh,
    onError: (e) => setError(e.message),
  });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <h1>Risk Register</h1>
      <div className="sub">Score = probability x impact (1 to 25). 15+ is critical.</div>

      {canWrite && (
        <form className="card form" style={{ marginBottom: 16 }}
          onSubmit={(e) => { e.preventDefault(); add.mutate(form); }}>
          <div><label>Project</label>
            <select value={form.project} onChange={set("project")} required>
              <option value="">Select</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.code}</option>)}
            </select></div>
          <div><label>Risk</label><input value={form.title} onChange={set("title")} required /></div>
          <div><label>Probability (1-5)</label><input type="number" min="1" max="5" value={form.probability} onChange={set("probability")} /></div>
          <div><label>Impact (1-5)</label><input type="number" min="1" max="5" value={form.impact} onChange={set("impact")} /></div>
          <div><label>Mitigation</label><input value={form.mitigation} onChange={set("mitigation")} /></div>
          <button disabled={add.isPending}>Add risk</button>
        </form>
      )}
      {error && <div className="error">{error}</div>}

      <div className="card">
        <table>
          <thead><tr><th>Project</th><th>Risk</th><th>P x I</th><th>Severity</th><th>Mitigation</th><th>Status</th></tr></thead>
          <tbody>
            {risks.map((r) => (
              <tr key={r.id}>
                <td>{code(r.project)}</td><td>{r.title}</td>
                <td>{r.probability} x {r.impact} = <b>{r.score}</b></td>
                <td><Badge value={r.severity} /></td><td>{r.mitigation}</td>
                <td>
                  <select value={r.status} disabled={!canWrite}
                    onChange={(e) => setStatus.mutate({ id: r.id, status: e.target.value })}>
                    <option value="open">Open</option><option value="mitigating">Mitigating</option>
                    <option value="occurred">Occurred</option><option value="closed">Closed</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
