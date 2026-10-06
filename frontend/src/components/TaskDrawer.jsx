import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, list } from "../api.js";

const STATUSES = [["todo", "To Do"], ["in_progress", "In Progress"], ["review", "In Review"], ["blocked", "Blocked"], ["done", "Done"]];
const PRIORITIES = [["low", "Low"], ["medium", "Medium"], ["high", "High"], ["critical", "Critical"]];

const toForm = (t) => ({
  title: t.title || "",
  description: t.description || "",
  status: t.status,
  priority: t.priority,
  assignee: t.assignee ?? "",
  sprint: t.sprint ?? "",
  start_date: t.start_date || "",
  due_date: t.due_date || "",
  estimate_hours: t.estimate_hours ?? 0,
  story_points: t.story_points ?? 0,
});

// Empty strings become null so cleared dates/assignee/sprint are saved as "none".
const toPayload = (f) => ({
  ...f,
  assignee: f.assignee === "" ? null : Number(f.assignee),
  sprint: f.sprint === "" ? null : Number(f.sprint),
  start_date: f.start_date || null,
  due_date: f.due_date || null,
  estimate_hours: f.estimate_hours === "" ? 0 : f.estimate_hours,
  story_points: f.story_points === "" ? 0 : f.story_points,
});

export default function TaskDrawer({ task, me, onClose }) {
  const qc = useQueryClient();
  const [form, setForm] = useState(toForm(task));
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");

  const canWrite = me && me.role !== "viewer";
  const canDelete = me && ["admin", "manager"].includes(me.role);
  const dirty = JSON.stringify(form) !== JSON.stringify(toForm(task));

  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: () => list("/users/") });
  const { data: sprints = [] } = useQuery({
    queryKey: ["sprints", task.project], queryFn: () => list(`/sprints/?project=${task.project}`),
  });
  const { data: comments = [] } = useQuery({
    queryKey: ["comments", task.id], queryFn: () => list(`/comments/?task=${task.id}`),
  });

  const { data: subtasks = [] } = useQuery({
    queryKey: ["subtasks", task.id], queryFn: () => list(`/tasks/?parent=${task.id}`),
  });
  const { data: deps = [] } = useQuery({
    queryKey: ["deps", task.id], queryFn: () => list(`/task-dependencies/?task=${task.id}`),
  });
  const { data: projectTasks = [] } = useQuery({
    queryKey: ["tasks-of-project", task.project], queryFn: () => list(`/tasks/?project=${task.project}&ordering=title`),
  });
  const [newSub, setNewSub] = useState("");
  const [depPick, setDepPick] = useState("");

  const addSub = useMutation({
    mutationFn: () => api("/tasks/", { method: "POST", body: { project: task.project, parent: task.id, title: newSub } }),
    onSuccess: () => { setNewSub(""); qc.invalidateQueries({ queryKey: ["subtasks", task.id] }); refresh(); },
    onError: (e) => setError(e.message),
  });
  const toggleSub = useMutation({
    mutationFn: ({ id, status }) => api(`/tasks/${id}/`, { method: "PATCH", body: { status } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["subtasks", task.id] }); refresh(); },
    onError: (e) => setError(e.message),
  });
  const addDep = useMutation({
    mutationFn: () => api("/task-dependencies/", { method: "POST", body: { task: task.id, depends_on: Number(depPick) } }),
    onSuccess: () => { setDepPick(""); qc.invalidateQueries({ queryKey: ["deps", task.id] }); },
    onError: (e) => setError(e.message),
  });
  const removeDep = useMutation({
    mutationFn: (id) => api(`/task-dependencies/${id}/`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deps", task.id] }),
    onError: (e) => setError(e.message),
  });
  const titleOf = (id) => projectTasks.find((t) => t.id === id)?.title || `Task #${id}`;
  const taken = new Set([task.id, ...deps.map((d) => d.depends_on)]);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["tasks"] });
    qc.invalidateQueries({ queryKey: ["overview"] });
    qc.invalidateQueries({ queryKey: ["workload"] });
    qc.invalidateQueries({ queryKey: ["overdue"] });
  };

  const save = useMutation({
    mutationFn: () => api(`/tasks/${task.id}/`, { method: "PATCH", body: toPayload(form) }),
    onSuccess: () => { refresh(); onClose(); },
    onError: (e) => setError(e.message),
  });
  const remove = useMutation({
    mutationFn: () => api(`/tasks/${task.id}/`, { method: "DELETE" }),
    onSuccess: () => { refresh(); onClose(); },
    onError: (e) => setError(e.message),
  });
  const addComment = useMutation({
    mutationFn: () => api("/comments/", { method: "POST", body: { task: task.id, body: comment } }),
    onSuccess: () => { setComment(""); qc.invalidateQueries({ queryKey: ["comments", task.id] }); },
    onError: (e) => setError(e.message),
  });

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const close = () => {
    if (dirty && !window.confirm("Discard unsaved changes?")) return;
    onClose();
  };

  return (
    <div className="overlay" onClick={close}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Task details">
        <div className="toolbar">
          <h2 style={{ margin: 0 }}>{task.project_code} task #{task.id}</h2>
          <button className="ghost" onClick={close}>Close</button>
        </div>

        <div className="stack">
          <div><label>Title</label>
            <input value={form.title} onChange={set("title")} disabled={!canWrite} /></div>
          <div><label>Description</label>
            <textarea rows={4} value={form.description} onChange={set("description")} disabled={!canWrite} /></div>

          <div className="form">
            <div><label>Status</label>
              <select value={form.status} onChange={set("status")} disabled={!canWrite}>
                {STATUSES.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
              </select></div>
            <div><label>Priority</label>
              <select value={form.priority} onChange={set("priority")} disabled={!canWrite}>
                {PRIORITIES.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
              </select></div>
            <div><label>Assignee</label>
              <select value={form.assignee} onChange={set("assignee")} disabled={!canWrite}>
                <option value="">Unassigned</option>
                {users.filter((u) => u.is_active && u.role !== "viewer").map((u) =>
                  <option key={u.id} value={u.id}>{u.full_name}</option>)}
              </select></div>
            <div><label>Sprint</label>
              <select value={form.sprint} onChange={set("sprint")} disabled={!canWrite}>
                <option value="">No sprint</option>
                {sprints.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select></div>
            <div><label>Start date</label>
              <input type="date" value={form.start_date} onChange={set("start_date")} disabled={!canWrite} /></div>
            <div><label>Due date</label>
              <input type="date" value={form.due_date} onChange={set("due_date")} disabled={!canWrite} /></div>
            <div><label>Estimate (hours)</label>
              <input type="number" min="0" step="0.5" value={form.estimate_hours} onChange={set("estimate_hours")} disabled={!canWrite} /></div>
            <div><label>Story points</label>
              <input type="number" min="0" value={form.story_points} onChange={set("story_points")} disabled={!canWrite} /></div>
          </div>

          {error && <div className="error">{error}</div>}

          {canWrite && (
            <div className="row">
              <button disabled={!dirty || save.isPending} onClick={() => { setError(""); save.mutate(); }}>
                {save.isPending ? "Saving..." : "Save changes"}
              </button>
              {canDelete && (
                <button className="ghost danger" disabled={remove.isPending}
                  onClick={() => window.confirm("Delete this task and its subtasks?") && remove.mutate()}>
                  Delete task
                </button>
              )}
            </div>
          )}

          <div>
            <h2>Subtasks ({subtasks.filter((s) => s.status === "done").length}/{subtasks.length} done)</h2>
            {subtasks.map((s) => (
              <label key={s.id} className="row" style={{ margin: "4px 0", color: "var(--ink)", fontSize: 14 }}>
                <input type="checkbox" style={{ width: "auto" }} checked={s.status === "done"} disabled={!canWrite}
                  onChange={(e) => toggleSub.mutate({ id: s.id, status: e.target.checked ? "done" : "todo" })} />
                <span style={{ textDecoration: s.status === "done" ? "line-through" : "none" }}>{s.title}</span>
              </label>
            ))}
            {canWrite && (
              <form className="row" onSubmit={(e) => { e.preventDefault(); if (newSub.trim()) addSub.mutate(); }}>
                <input placeholder="Add a subtask" value={newSub} onChange={(e) => setNewSub(e.target.value)} />
                <button disabled={addSub.isPending || !newSub.trim()}>Add</button>
              </form>
            )}
          </div>

          <div>
            <h2>Depends on ({deps.length})</h2>
            {deps.length === 0 && <p className="muted">No dependencies.</p>}
            {deps.map((d) => (
              <div key={d.id} className="row" style={{ justifyContent: "space-between", margin: "4px 0" }}>
                <span>{titleOf(d.depends_on)}</span>
                {canDelete && <button className="ghost danger" onClick={() => removeDep.mutate(d.id)}>Remove</button>}
              </div>
            ))}
            {canWrite && (
              <form className="row" onSubmit={(e) => { e.preventDefault(); if (depPick) addDep.mutate(); }}>
                <select value={depPick} onChange={(e) => setDepPick(e.target.value)}>
                  <option value="">Must finish first...</option>
                  {projectTasks.filter((t) => !taken.has(t.id)).map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
                </select>
                <button disabled={!depPick || addDep.isPending}>Add</button>
              </form>
            )}
          </div>

          <div>
            <h2>Comments ({comments.length})</h2>
            {comments.length === 0 && <p className="muted">No comments yet.</p>}
            {comments.map((c) => (
              <div key={c.id} className="comment">
                <b>{c.author_name || "Deleted user"}</b>
                <span className="muted"> · {new Date(c.created_at).toLocaleString()}</span>
                <div>{c.body}</div>
              </div>
            ))}
            {canWrite && (
              <form className="row" onSubmit={(e) => { e.preventDefault(); if (comment.trim()) addComment.mutate(); }}>
                <input placeholder="Write a comment" value={comment} onChange={(e) => setComment(e.target.value)} />
                <button disabled={addComment.isPending || !comment.trim()}>Post</button>
              </form>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
