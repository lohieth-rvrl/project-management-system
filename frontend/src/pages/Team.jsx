import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api.js";
import Chart from "../components/Chart.jsx";

export default function Team() {
  const { data = [], isLoading } = useQuery({ queryKey: ["workload"], queryFn: () => api("/analytics/workload/") });
  const people = data.filter((p) => p.role !== "viewer");

  const option = useMemo(() => ({
    title: { text: "Open estimate vs 7-day logged hours", textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    xAxis: { type: "category", data: people.map((p) => p.username) },
    yAxis: { type: "value", name: "hours" },
    series: [
      { name: "Open estimate (h)", type: "bar", data: people.map((p) => p.open_estimate_hours), itemStyle: { color: "#2f6fd6" } },
      { name: "Logged last 7 days (h)", type: "bar", data: people.map((p) => p.logged_hours_7d), itemStyle: { color: "#1f9d55" } },
      { name: "Weekly capacity (h)", type: "line", data: people.map((p) => p.weekly_capacity), itemStyle: { color: "#d98e04" } },
    ],
  }), [data]);

  if (isLoading) return <p>Loading...</p>;

  return (
    <>
      <h1>Team Workload</h1>
      <div className="sub">An assignee is flagged when open estimated work exceeds two weeks of capacity</div>
      <div className="card" style={{ marginBottom: 16 }}><Chart option={option} /></div>
      <div className="card">
        <table>
          <thead><tr><th>Person</th><th>Role</th><th>Open tasks</th><th>Overdue</th><th>Open est. (h)</th><th>Logged 7d (h)</th><th>Utilization</th><th></th></tr></thead>
          <tbody>
            {people.map((p) => (
              <tr key={p.user}>
                <td><b>{p.username}</b></td><td>{p.role}</td><td>{p.open_tasks}</td>
                <td style={{ color: p.overdue_tasks ? "var(--bad)" : undefined }}>{p.overdue_tasks}</td>
                <td>{p.open_estimate_hours}</td><td>{p.logged_hours_7d}</td><td>{p.utilization_percent}%</td>
                <td>{p.overloaded && <span className="badge red">Overloaded</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
