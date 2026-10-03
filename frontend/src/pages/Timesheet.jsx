import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOutletContext } from "react-router-dom";
import { api, list } from "../api.js";
import Pagination from "../components/Pagination.jsx";
import usePaged from "../components/usePaged.js";

const today = () => new Date().toISOString().slice(0, 10);

export default function Timesheet() {
  const { me } = useOutletContext();
  const qc = useQueryClient();
  const [form, setForm] = useState({ task: "", work_date: today(), hours: "", note: "" });
  const [error, setError] = useState("");

  const pg = usePaged("time", "/time-entries/");
  const entries = pg.rows;
  const { data: tasks = [] } = useQuery({ queryKey: ["tasks-all"], queryFn: () => list("/tasks/?ordering=title") });

  const canApprove = me && ["admin", "manager", "lead"].includes(me.role);
  const canWrite = me && me.role !== "viewer";
  const pageTotal = entries.reduce((s, e) => s + Number(e.hours), 0);

  const refresh = () => { qc.invalidateQueries({ queryKey: ["time"] }); qc.invalidateQueries({ queryKey: ["overview"] }); };

  const add = useMutation({
    mutationFn: (body) => api("/time-entries/", { method: "POST", body }),
    onSuccess: () => { refresh(); setForm({ ...form, hours: "", note: "" }); setError(""); },
    onError: (e) => setError(e.message),
  });
  const approve = useMutation({
    mutationFn: (id) => api(`/time-entries/${id}/approve/`, { method: "POST" }),
    onSuccess: refresh,
    onError: (e) => setError(e.message),
  });

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <h1>Timesheet</h1>
      <div className="sub">{canApprove ? "All logged time. Approve entries below." : "Your logged time"} Hours on this page: <b>{pageTotal}h</b></div>

      {canWrite && (
        <form className="card form" style={{ marginBottom: 16 }}
          onSubmit={(e) => { e.preventDefault(); add.mutate(form); }}>
          <div><label>Task</label>
            <select value={form.task} onChange={set("task")} required>
              <option value="">Select task</option>
              {tasks.map((t) => <option key={t.id} value={t.id}>{t.project_code}: {t.title}</option>)}
            </select></div>
          <div><label>Date</label><input type="date" value={form.work_date} onChange={set("work_date")} required /></div>
          <div><label>Hours</label><input type="number" step="0.25" min="0.25" max="24" value={form.hours} onChange={set("hours")} required /></div>
          <div><label>Note</label><input value={form.note} onChange={set("note")} /></div>
          <button disabled={add.isPending}>Log time</button>
        </form>
      )}
      {error && <div className="error">{error}</div>}

      <div className="card">
        <table>
          <thead><tr><th>Date</th><th>User</th><th>Task</th><th>Hours</th><th>Note</th><th>Status</th></tr></thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id}>
                <td>{e.work_date}</td><td>{e.username}</td><td>{e.task_title}</td><td>{e.hours}</td><td>{e.note}</td>
                <td>{e.approved ? <span className="badge done">Approved</span>
                  : canApprove ? <button className="ghost" onClick={() => approve.mutate(e.id)}>Approve</button>
                  : <span className="badge">Pending</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={pg.page} pageSize={pg.pageSize} count={pg.count} onPage={pg.setPage} onPageSize={pg.setPageSize} />
      </div>
    </>
  );
}
