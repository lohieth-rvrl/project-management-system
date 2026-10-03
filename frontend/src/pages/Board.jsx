import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOutletContext } from "react-router-dom";
import { api, list } from "../api.js";
import Badge from "../components/Badge.jsx";
import TaskDrawer from "../components/TaskDrawer.jsx";

const COLUMNS = [
  ["todo", "To Do"], ["in_progress", "In Progress"], ["review", "In Review"],
  ["blocked", "Blocked"], ["done", "Done"],
];

export default function Board() {
  const { me } = useOutletContext();
  const qc = useQueryClient();
  const [project, setProject] = useState("");
  const [over, setOver] = useState(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const [openTask, setOpenTask] = useState(null);

  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: () => list("/projects/") });
  const pid = project || projects[0]?.id || "";
  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["tasks", pid], enabled: !!pid, queryFn: () => list(`/tasks/?project=${pid}`),
  });

  const canWrite = me && me.role !== "viewer";

  const move = useMutation({
    mutationFn: ({ id, status }) => api(`/tasks/${id}/`, { method: "PATCH", body: { status } }),
    // optimistic update so the card jumps immediately
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ["tasks", pid] });
      const prev = qc.getQueryData(["tasks", pid]);
      qc.setQueryData(["tasks", pid], (old) => old.map((t) => (t.id === id ? { ...t, status } : t)));
      return { prev };
    },
    onError: (e, _v, ctx) => { qc.setQueryData(["tasks", pid], ctx.prev); setError(e.message); },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["tasks", pid] });
      qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  const add = useMutation({
    mutationFn: (body) => api("/tasks/", { method: "POST", body }),
    onSuccess: () => { setTitle(""); qc.invalidateQueries({ queryKey: ["tasks", pid] }); },
    onError: (e) => setError(e.message),
  });

  const drop = (status) => (e) => {
    e.preventDefault();
    setOver(null);
    const id = Number(e.dataTransfer.getData("text/plain"));
    const task = tasks.find((t) => t.id === id);
    if (task && task.status !== status) move.mutate({ id, status });
  };

  return (
    <>
      <div className="toolbar">
        <div><h1>Task Board</h1><div className="sub">Drag cards between columns to update status</div></div>
        <select value={pid} onChange={(e) => setProject(e.target.value)}>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.code} - {p.name}</option>)}
        </select>
      </div>

      {canWrite && pid && (
        <form className="card" style={{ marginBottom: 16, display: "flex", gap: 8 }}
          onSubmit={(e) => { e.preventDefault(); if (title.trim()) add.mutate({ project: pid, title }); }}>
          <input placeholder="Add a task and press Enter" value={title} onChange={(e) => setTitle(e.target.value)} />
          <button disabled={add.isPending}>Add</button>
        </form>
      )}
      {error && <div className="error">{error}</div>}

      {isLoading ? <p>Loading...</p> : (
        <div className="board">
          {COLUMNS.map(([key, name]) => {
            const items = tasks.filter((t) => t.status === key);
            return (
              <div key={key} className={`col ${over === key ? "over" : ""}`}
                onDragOver={(e) => { if (canWrite) { e.preventDefault(); setOver(key); } }}
                onDragLeave={() => setOver(null)}
                onDrop={canWrite ? drop(key) : undefined}>
                <h3>{name} ({items.length})</h3>
                {items.map((t) => (
                  <div key={t.id} className="tcard" draggable={canWrite} onClick={() => setOpenTask(t)}
                    onDragStart={(e) => e.dataTransfer.setData("text/plain", String(t.id))}>
                    <div>{t.title}</div>
                    <div className="meta">
                      <Badge value={t.priority} />
                      <span>{t.assignee_name || "Unassigned"}{t.due_date ? ` · ${t.due_date}` : ""}</span>
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}
      {openTask && <TaskDrawer key={openTask.id} task={openTask} me={me} onClose={() => setOpenTask(null)} />}
    </>
  );
}
