import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { api, list } from "../api.js";
import Badge, { label } from "../components/Badge.jsx";
import Pagination from "../components/Pagination.jsx";
import TaskDrawer from "../components/TaskDrawer.jsx";
import usePaged from "../components/usePaged.js";

const STATUSES = ["todo", "in_progress", "review", "blocked", "done"];
const PRIORITIES = ["low", "medium", "high", "critical"];
const SORTS = [
  ["-created_at", "Newest first"], ["due_date", "Due date (soonest)"], ["-due_date", "Due date (latest)"],
  ["-priority", "Priority"], ["-updated_at", "Recently updated"],
];

export default function Tasks() {
  const { me } = useOutletContext();
  const [params, setParams] = useSearchParams();
  const [f, setF] = useState({ search: "", project: "", status: "", priority: "", assignee: "", overdue: false, unassigned: false, ordering: "-created_at" });
  const [open, setOpen] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const { data: projects = [] } = useQuery({ queryKey: ["projects-all"], queryFn: () => list("/projects/") });
  const { data: users = [] } = useQuery({ queryKey: ["users-all"], queryFn: () => list("/users/") });

  const qs = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => { if (v !== "" && v !== false) qs.set(k, v === true ? "true" : v); });
  const pg = usePaged("tasks", `/tasks/?${qs.toString()}`);

  // Deep link from global search: /tasks?task=12 opens that task
  const wanted = params.get("task");
  useEffect(() => {
    if (!wanted) return;
    api(`/tasks/${wanted}/`).then(setOpen).catch(() => {});
  }, [wanted]);

  const close = () => {
    setOpen(null);
    if (wanted) { params.delete("task"); setParams(params, { replace: true }); }
  };

  return (
    <>
      <h1>Tasks</h1>
      <div className="sub">All work items across projects. Click a row for details.</div>

      <div className="card form" style={{ marginBottom: 16 }}>
        <div><label>Search</label><input placeholder="Title or description" value={f.search} onChange={set("search")} /></div>
        <div><label>Project</label><select value={f.project} onChange={set("project")}><option value="">All</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.code}</option>)}</select></div>
        <div><label>Status</label><select value={f.status} onChange={set("status")}><option value="">All</option>{STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></div>
        <div><label>Priority</label><select value={f.priority} onChange={set("priority")}><option value="">All</option>{PRIORITIES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></div>
        <div><label>Assignee</label><select value={f.assignee} onChange={set("assignee")}><option value="">Anyone</option>{users.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}</select></div>
        <div><label>Sort</label><select value={f.ordering} onChange={set("ordering")}>{SORTS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></div>
        <div className="row"><label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={f.overdue} onChange={set("overdue")} /> Overdue</label></div>
        <div className="row"><label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={f.unassigned} onChange={set("unassigned")} /> Unassigned</label></div>
      </div>

      <div className="card">
        {pg.isLoading ? <p>Loading...</p> : pg.rows.length === 0 ? <p className="muted">No tasks match these filters.</p> : (
          <table>
            <thead><tr><th>Project</th><th>Task</th><th>Status</th><th>Priority</th><th>Assignee</th><th>Due</th><th>Est. h</th></tr></thead>
            <tbody>
              {pg.rows.map((t) => (
                <tr key={t.id} style={{ cursor: "pointer" }} onClick={() => setOpen(t)}>
                  <td>{t.project_code}</td><td>{t.title}</td><td><Badge value={t.status} /></td><td><Badge value={t.priority} /></td>
                  <td>{t.assignee_name || "-"}</td><td>{t.due_date || "-"}</td><td>{t.estimate_hours}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <Pagination page={pg.page} pageSize={pg.pageSize} count={pg.count} onPage={pg.setPage} onPageSize={pg.setPageSize} />
      </div>
      {open && <TaskDrawer key={open.id} task={open} me={me} onClose={close} />}
    </>
  );
}
