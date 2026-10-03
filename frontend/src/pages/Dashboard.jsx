import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api.js";
import Chart from "../components/Chart.jsx";
import { label } from "../components/Badge.jsx";

const COLORS = {
  todo: "#9aa5b8", in_progress: "#2f6fd6", review: "#8e6bd6", blocked: "#d64545", done: "#1f9d55",
  green: "#1f9d55", amber: "#d98e04", red: "#d64545",
};

const pie = (obj, title) => ({
  title: { text: title, textStyle: { fontSize: 14 } },
  tooltip: { trigger: "item" },
  legend: { bottom: 0 },
  series: [{
    type: "pie", radius: ["45%", "70%"],
    data: Object.entries(obj || {}).map(([k, v]) => ({
      name: label(k), value: v, itemStyle: { color: COLORS[k] },
    })),
  }],
});

function Kpi({ l, v, bad }) {
  return (
    <div className={`card kpi ${bad && v > 0 ? "bad" : ""}`}>
      <div className="v">{v}</div>
      <div className="l">{l}</div>
    </div>
  );
}

export default function Dashboard() {
  const { data: o, isLoading, error } = useQuery({
    queryKey: ["overview"], queryFn: () => api("/analytics/overview/"),
  });
  const { data: velocity = [] } = useQuery({
    queryKey: ["velocity"], queryFn: () => api("/analytics/velocity/"),
  });
  const { data: overdue = [] } = useQuery({
    queryKey: ["overdue"], queryFn: () => api("/analytics/overdue/"),
  });

  const velOpt = useMemo(() => ({
    title: { text: "Sprint velocity (story points)", textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    xAxis: { type: "category", data: velocity.map((v) => `${v.sprint} (P${v.project})`) },
    yAxis: { type: "value" },
    series: [
      { name: "Planned", type: "bar", data: velocity.map((v) => v.planned_points), itemStyle: { color: "#9aa5b8" } },
      { name: "Completed", type: "bar", data: velocity.map((v) => v.completed_points), itemStyle: { color: "#1f9d55" } },
    ],
  }), [velocity]);

  if (isLoading) return <p>Loading dashboard...</p>;
  if (error) return <p className="error">{error.message}</p>;

  return (
    <>
      <h1>Dashboard</h1>
      <div className="sub">Organisation-wide view of projects, work and risk</div>

      <div className="grid kpis">
        <Kpi l="Total tasks" v={o.total_tasks} />
        <Kpi l="Completion rate" v={`${o.completion_rate}%`} />
        <Kpi l="Overdue tasks" v={o.overdue_tasks} bad />
        <Kpi l="Unassigned open tasks" v={o.unassigned_open_tasks} bad />
        <Kpi l="Critical open risks" v={o.open_critical_risks} bad />
        <Kpi l="Hours logged (7 days)" v={o.hours_last_7_days} />
      </div>

      <div className="grid two">
        <div className="card"><Chart option={pie(o.tasks_by_status, "Tasks by status")} /></div>
        <div className="card"><Chart option={pie(o.projects_by_health, "Active project health")} /></div>
        <div className="card"><Chart option={pie(o.tasks_by_priority, "Open tasks by priority")} /></div>
        <div className="card"><Chart option={velOpt} /></div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2>Overdue tasks</h2>
        {overdue.length === 0 ? <p className="muted">Nothing overdue.</p> : (
          <table>
            <thead><tr><th>Task</th><th>Project</th><th>Assignee</th><th>Due</th><th>Days late</th></tr></thead>
            <tbody>
              {overdue.map((t) => (
                <tr key={t.id}>
                  <td>{t.title}</td><td>{t.project}</td><td>{t.assignee || "-"}</td>
                  <td>{t.due_date}</td><td style={{ color: "var(--bad)" }}>{t.days_late}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
