import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { list } from "../api.js";

const DAY = 86400000;
const COLORS = { todo: "#94a3b8", in_progress: "#2563eb", review: "#9333ea", blocked: "#dc2626", done: "#16a34a" };
const toTime = (d) => new Date(`${d}T00:00:00`).getTime();
const fmt = (t) => new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short" });

// Timeline of a project's tasks (bars from start to due date) and milestones (diamonds).
export default function Gantt({ project, milestones }) {
  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["gantt", project.id], queryFn: () => list(`/tasks/?project=${project.id}`),
  });

  const model = useMemo(() => {
    const rows = tasks.filter((t) => t.start_date || t.due_date).map((t) => {
      const s = toTime(t.start_date || t.due_date);
      const e = toTime(t.due_date || t.start_date);
      return { id: t.id, title: t.title, status: t.status, start: Math.min(s, e), end: Math.max(s, e) + DAY };
    }).sort((a, b) => a.start - b.start);
    const ms = milestones.map((m) => ({ id: m.id, name: m.name, at: toTime(m.due_date), status: m.status }));
    const points = [...rows.flatMap((r) => [r.start, r.end]), ...ms.map((m) => m.at),
      ...(project.start_date ? [toTime(project.start_date)] : []), ...(project.end_date ? [toTime(project.end_date) + DAY] : [])];
    if (!points.length) return null;
    const min = Math.min(...points) - 2 * DAY;
    const max = Math.max(...points) + 2 * DAY;
    return { rows, ms, min, span: max - min, unscheduled: tasks.length - rows.length };
  }, [tasks, milestones, project]);

  if (isLoading) return <p>Loading timeline...</p>;
  if (!model) return <p className="muted">Give tasks a start or due date, or add milestones, to see the timeline.</p>;

  const pct = (t) => `${((t - model.min) / model.span) * 100}%`;
  const today = Date.now();
  const ticks = Array.from({ length: 6 }, (_, i) => model.min + (model.span * i) / 5);

  return (
    <div className="gantt" aria-label="Project timeline">
      <div style={{ position: "relative", height: 18, marginLeft: 180 }}>
        {ticks.map((t) => <span key={t} className="muted" style={{ position: "absolute", left: pct(t), fontSize: 11 }}>{fmt(t)}</span>)}
      </div>
      {model.ms.map((m) => (
        <div key={`m${m.id}`} style={{ display: "flex", alignItems: "center", height: 26 }}>
          <div style={{ width: 180, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>&#9670; {m.name}</div>
          <div style={{ position: "relative", flex: 1, height: 26, borderLeft: "1px solid #e2e8f0" }}>
            <span title={`${m.name} - ${fmt(m.at)} (${m.status})`}
              style={{ position: "absolute", left: pct(m.at), top: 4, width: 14, height: 14, background: m.status === "done" ? "#16a34a" : m.status === "missed" ? "#dc2626" : "#f59e0b", transform: "rotate(45deg)" }} />
          </div>
        </div>
      ))}
      {model.rows.map((r) => (
        <div key={r.id} style={{ display: "flex", alignItems: "center", height: 26 }}>
          <div style={{ width: 180, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.title}>{r.title}</div>
          <div style={{ position: "relative", flex: 1, height: 26, borderLeft: "1px solid #e2e8f0" }}>
            <div data-testid="gantt-bar" title={`${r.title}: ${fmt(r.start)} to ${fmt(r.end - DAY)} (${r.status})`}
              style={{ position: "absolute", top: 5, height: 16, borderRadius: 3, background: COLORS[r.status] || "#94a3b8",
                left: pct(r.start), width: `${Math.max(((r.end - r.start) / model.span) * 100, 0.8)}%` }} />
          </div>
        </div>
      ))}
      <div style={{ position: "relative", marginLeft: 180, height: 0 }}>
        {today >= model.min && today <= model.min + model.span && (
          <div title="Today" style={{ position: "absolute", left: pct(today), bottom: 0, height: (model.rows.length + model.ms.length) * 26 + 4, borderLeft: "2px dashed #f97316", transform: "translateY(0)" }} />
        )}
      </div>
      {model.unscheduled > 0 && <p className="muted">{model.unscheduled} task(s) have no dates and are not shown.</p>}
    </div>
  );
}
