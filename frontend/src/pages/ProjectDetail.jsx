import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { api, list } from "../api.js";
import Badge, { label } from "../components/Badge.jsx";

const STATUSES = ["planning", "active", "on_hold", "completed", "cancelled"];
const HEALTH = ["green", "amber", "red"];

function useCrud(listKey, path, projectId, onError) {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: [listKey, projectId] });
  const opts = { onSuccess: refresh, onError: (e) => onError(e.message) };
  return {
    create: useMutation({ mutationFn: (b) => api(path, { method: "POST", body: { ...b, project: projectId } }), ...opts }),
    patch: useMutation({ mutationFn: ({ id, ...b }) => api(`${path}${id}/`, { method: "PATCH", body: b }), ...opts }),
    remove: useMutation({ mutationFn: (id) => api(`${path}${id}/`, { method: "DELETE" }), ...opts }),
  };
}

export default function ProjectDetail() {
  const { id } = useParams();
  const pid = Number(id);
  const nav = useNavigate();
  const qc = useQueryClient();
  const { me } = useOutletContext();
  const canWrite = me && me.role !== "viewer";
  const canDelete = me && ["admin", "manager"].includes(me.role);
  const [error, setError] = useState("");
  const [form, setForm] = useState(null);

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", pid], queryFn: () => api(`/projects/${pid}/`),
  });
  const { data: users = [] } = useQuery({ queryKey: ["users-all"], queryFn: () => list("/users/") });
  const { data: sprints = [] } = useQuery({ queryKey: ["sprints", pid], queryFn: () => list(`/sprints/?project=${pid}`) });
  const { data: milestones = [] } = useQuery({ queryKey: ["milestones", pid], queryFn: () => list(`/milestones/?project=${pid}`) });
  const { data: members = [] } = useQuery({ queryKey: ["members", pid], queryFn: () => list(`/project-members/?project=${pid}`) });

  const sprintApi = useCrud("sprints", "/sprints/", pid, setError);
  const msApi = useCrud("milestones", "/milestones/", pid, setError);
  const memApi = useCrud("members", "/project-members/", pid, setError);

  const f = form || (project && {
    code: project.code, name: project.name, description: project.description || "", status: project.status,
    health: project.health, start_date: project.start_date || "", end_date: project.end_date || "",
    budget: project.budget, hourly_rate: project.hourly_rate, owner: project.owner ?? "",
  });
  const set = (k) => (e) => setForm({ ...f, [k]: e.target.value });

  const save = useMutation({
    mutationFn: () => api(`/projects/${pid}/`, {
      method: "PATCH",
      body: { ...f, owner: f.owner === "" ? null : Number(f.owner), start_date: f.start_date || null, end_date: f.end_date || null },
    }),
    onSuccess: () => {
      setForm(null); setError("");
      qc.invalidateQueries({ queryKey: ["project", pid] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e) => setError(e.message),
  });
  const del = useMutation({
    mutationFn: () => api(`/projects/${pid}/`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["projects"] }); nav("/projects"); },
    onError: (e) => setError(e.message),
  });

  const [sp, setSp] = useState({ name: "", start_date: "", end_date: "", goal: "" });
  const [ms, setMs] = useState({ name: "", due_date: "" });
  const [mem, setMem] = useState({ user: "", role: "Contributor", allocation_percent: 100 });

  if (isLoading || !f) return <p>Loading...</p>;
  const memberIds = new Set(members.map((m) => m.user));

  return (
    <>
      <div className="toolbar">
        <div><Link to="/projects">&larr; Projects</Link><h1>{project.code}: {project.name}</h1></div>
        <div className="row"><Badge value={project.status} /><Badge value={project.health} /></div>
      </div>
      {error && <div className="error">{error}</div>}

      <form className="card form" onSubmit={(e) => { e.preventDefault(); setError(""); save.mutate(); }}>
        <div><label>Code</label><input value={f.code} onChange={set("code")} disabled={!canWrite} required /></div>
        <div><label>Name</label><input value={f.name} onChange={set("name")} disabled={!canWrite} required /></div>
        <div><label>Status</label><select value={f.status} onChange={set("status")} disabled={!canWrite}>{STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></div>
        <div><label>Health</label><select value={f.health} onChange={set("health")} disabled={!canWrite}>{HEALTH.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></div>
        <div><label>Owner</label><select value={f.owner} onChange={set("owner")} disabled={!canWrite}><option value="">None</option>{users.filter((u) => u.is_active).map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}</select></div>
        <div><label>Start</label><input type="date" value={f.start_date} onChange={set("start_date")} disabled={!canWrite} /></div>
        <div><label>End</label><input type="date" value={f.end_date} onChange={set("end_date")} disabled={!canWrite} /></div>
        <div><label>Budget</label><input type="number" min="0" value={f.budget} onChange={set("budget")} disabled={!canWrite} /></div>
        <div><label>Cost per hour</label><input type="number" min="0" value={f.hourly_rate} onChange={set("hourly_rate")} disabled={!canWrite} /></div>
        <div style={{ gridColumn: "1 / -1" }}><label>Description</label><textarea rows={3} value={f.description} onChange={set("description")} disabled={!canWrite} /></div>
        {canWrite && (
          <div className="row">
            <button disabled={!form || save.isPending}>Save changes</button>
            {canDelete && <button type="button" className="ghost danger" onClick={() => window.confirm(`Delete ${project.code} and ALL its tasks, risks and time entries? This cannot be undone.`) && del.mutate()}>Delete project</button>}
          </div>
        )}
      </form>

      <div className="grid two" style={{ marginTop: 16 }}>
        <div className="card">
          <h2>Sprints ({sprints.length})</h2>
          <table><thead><tr><th>Name</th><th>Dates</th><th>Goal</th><th></th></tr></thead><tbody>
            {sprints.map((s) => (
              <tr key={s.id}><td><b>{s.name}</b></td><td>{s.start_date} to {s.end_date}</td><td>{s.goal}</td>
                <td>{canDelete && <button className="ghost danger" onClick={() => window.confirm("Delete sprint? Its tasks stay, without a sprint.") && sprintApi.remove.mutate(s.id)}>Delete</button>}</td></tr>
            ))}
          </tbody></table>
          {canWrite && (
            <form className="form" style={{ marginTop: 12 }} onSubmit={(e) => { e.preventDefault(); setError(""); sprintApi.create.mutate(sp, { onSuccess: () => setSp({ name: "", start_date: "", end_date: "", goal: "" }) }); }}>
              <div><label>Name</label><input value={sp.name} onChange={(e) => setSp({ ...sp, name: e.target.value })} required /></div>
              <div><label>Start</label><input type="date" value={sp.start_date} onChange={(e) => setSp({ ...sp, start_date: e.target.value })} required /></div>
              <div><label>End</label><input type="date" value={sp.end_date} onChange={(e) => setSp({ ...sp, end_date: e.target.value })} required /></div>
              <div><label>Goal</label><input value={sp.goal} onChange={(e) => setSp({ ...sp, goal: e.target.value })} /></div>
              <button>Add sprint</button>
            </form>
          )}
        </div>

        <div className="card">
          <h2>Milestones ({milestones.length})</h2>
          <table><thead><tr><th>Name</th><th>Due</th><th>Status</th><th></th></tr></thead><tbody>
            {milestones.map((m) => (
              <tr key={m.id}><td><b>{m.name}</b></td><td>{m.due_date}</td>
                <td><select value={m.status} disabled={!canWrite} onChange={(e) => msApi.patch.mutate({ id: m.id, status: e.target.value })}>
                  <option value="pending">Pending</option><option value="done">Done</option><option value="missed">Missed</option></select></td>
                <td>{canDelete && <button className="ghost danger" onClick={() => window.confirm("Delete milestone?") && msApi.remove.mutate(m.id)}>Delete</button>}</td></tr>
            ))}
          </tbody></table>
          {canWrite && (
            <form className="form" style={{ marginTop: 12 }} onSubmit={(e) => { e.preventDefault(); setError(""); msApi.create.mutate(ms, { onSuccess: () => setMs({ name: "", due_date: "" }) }); }}>
              <div><label>Name</label><input value={ms.name} onChange={(e) => setMs({ ...ms, name: e.target.value })} required /></div>
              <div><label>Due</label><input type="date" value={ms.due_date} onChange={(e) => setMs({ ...ms, due_date: e.target.value })} required /></div>
              <button>Add milestone</button>
            </form>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2>Team ({members.length})</h2>
        <table><thead><tr><th>Person</th><th>Role on project</th><th>Allocation</th><th></th></tr></thead><tbody>
          {members.map((m) => (
            <tr key={m.id}><td><b>{m.username}</b></td><td>{m.role}</td><td>{m.allocation_percent}%</td>
              <td>{canDelete && <button className="ghost danger" onClick={() => memApi.remove.mutate(m.id)}>Remove</button>}</td></tr>
          ))}
        </tbody></table>
        {canWrite && (
          <form className="form" style={{ marginTop: 12 }} onSubmit={(e) => { e.preventDefault(); setError(""); memApi.create.mutate({ ...mem, user: Number(mem.user) }, { onSuccess: () => setMem({ ...mem, user: "" }) }); }}>
            <div><label>Person</label><select value={mem.user} onChange={(e) => setMem({ ...mem, user: e.target.value })} required>
              <option value="">Select</option>{users.filter((u) => u.is_active && !memberIds.has(u.id)).map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}</select></div>
            <div><label>Role on project</label><input value={mem.role} onChange={(e) => setMem({ ...mem, role: e.target.value })} /></div>
            <div><label>Allocation %</label><input type="number" min="0" max="100" value={mem.allocation_percent} onChange={(e) => setMem({ ...mem, allocation_percent: e.target.value })} /></div>
            <button>Add to team</button>
          </form>
        )}
      </div>
    </>
  );
}
