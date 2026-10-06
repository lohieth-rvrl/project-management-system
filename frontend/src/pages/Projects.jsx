import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useOutletContext } from "react-router-dom";
import { api } from "../api.js";
import Badge from "../components/Badge.jsx";
import Pagination from "../components/Pagination.jsx";
import usePaged from "../components/usePaged.js";

const blank = { code: "", name: "", status: "planning", budget: "", hourly_rate: "", start_date: "", end_date: "" };

export default function Projects() {
  const { me } = useOutletContext();
  const qc = useQueryClient();
  const [form, setForm] = useState(blank);
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  const pg = usePaged("projects", "/projects/");
  const projects = pg.rows;
  const isLoading = pg.isLoading;
  const { data: summary } = useQuery({
    queryKey: ["summary", selected], enabled: !!selected,
    queryFn: () => api(`/analytics/projects/${selected}/summary/`),
  });

  const canWrite = me && me.role !== "viewer";

  const create = useMutation({
    mutationFn: (body) => api("/projects/", { method: "POST", body }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["projects"] }); setForm(blank); setShow(false); setError(""); },
    onError: (e) => setError(e.message),
  });

  const submit = (e) => {
    e.preventDefault();
    const body = { ...form, owner: me.id };
    ["budget", "hourly_rate"].forEach((k) => { body[k] = body[k] === "" ? 0 : body[k]; });
    ["start_date", "end_date"].forEach((k) => { if (!body[k]) delete body[k]; });
    create.mutate(body);
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <div className="toolbar">
        <div><h1>Projects</h1><div className="sub">Select a project row to see its progress and budget</div></div>
        {canWrite && <button onClick={() => setShow(!show)}>{show ? "Cancel" : "New project"}</button>}
      </div>

      {show && (
        <form className="card form" onSubmit={submit} style={{ marginBottom: 16 }}>
          <div><label>Code</label><input value={form.code} onChange={set("code")} required /></div>
          <div><label>Name</label><input value={form.name} onChange={set("name")} required /></div>
          <div><label>Budget</label><input type="number" min="0" value={form.budget} onChange={set("budget")} /></div>
          <div><label>Cost per hour</label><input type="number" min="0" value={form.hourly_rate} onChange={set("hourly_rate")} /></div>
          <div><label>Start</label><input type="date" value={form.start_date} onChange={set("start_date")} /></div>
          <div><label>End</label><input type="date" value={form.end_date} onChange={set("end_date")} /></div>
          <button disabled={create.isPending}>Create</button>
          {error && <div className="error" style={{ gridColumn: "1 / -1" }}>{error}</div>}
        </form>
      )}

      <div className="card">
        {isLoading ? <p>Loading...</p> : (
          <table>
            <thead><tr><th>Code</th><th>Name</th><th>Status</th><th>Health</th><th>Progress</th><th>Owner</th><th>End</th></tr></thead>
            <tbody>
              {projects.map((p) => {
                const pct = p.task_count ? Math.round((p.done_count / p.task_count) * 100) : 0;
                return (
                  <tr key={p.id} onClick={() => setSelected(p.id)} style={{ cursor: "pointer", background: selected === p.id ? "#f0f5ff" : undefined }}>
                    <td><Link to={`/projects/${p.id}`} onClick={(e) => e.stopPropagation()}><b>{p.code}</b></Link></td><td>{p.name}</td>
                    <td><Badge value={p.status} /></td><td><Badge value={p.health} /></td>
                    <td style={{ minWidth: 140 }}>
                      <div className="bar"><i style={{ width: `${pct}%` }} /></div>
                      <span className="muted">{p.done_count}/{p.task_count} ({pct}%)</span>
                    </td>
                    <td>{p.owner_name || "-"}</td><td>{p.end_date || "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <Pagination page={pg.page} pageSize={pg.pageSize} count={pg.count} onPage={pg.setPage} onPageSize={pg.setPageSize} />
      </div>

      {summary && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2>{summary.code}: {summary.name}</h2>
          <div className="grid kpis">
            <div className="kpi"><div className="v">{summary.progress_percent}%</div><div className="l">Progress</div></div>
            <div className={`kpi ${summary.overdue_tasks ? "bad" : ""}`}><div className="v">{summary.overdue_tasks}</div><div className="l">Overdue tasks</div></div>
            <div className="kpi"><div className="v">{summary.logged_hours}h</div><div className="l">Logged of {summary.estimated_hours}h estimated</div></div>
            <div className={`kpi ${summary.budget_used_percent > 100 ? "bad" : ""}`}>
              <div className="v">{summary.budget_used_percent == null ? "-" : `${summary.budget_used_percent}%`}</div>
              <div className="l">Budget used ({summary.cost_to_date.toLocaleString()} of {summary.budget.toLocaleString()})</div>
            </div>
            <div className="kpi"><div className="v">{summary.open_risks}</div><div className="l">Open risks</div></div>
            <div className={`kpi ${summary.milestones_missed ? "bad" : ""}`}><div className="v">{summary.milestones_missed}</div><div className="l">Missed milestones</div></div>
          </div>
        </div>
      )}
    </>
  );
}
