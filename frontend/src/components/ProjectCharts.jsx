import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api.js";
import Chart from "./Chart.jsx";

export default function ProjectCharts({ project }) {
  const [unit, setUnit] = useState("tasks");
  const { data: bd } = useQuery({
    queryKey: ["burndown", project.id, unit], queryFn: () => api(`/analytics/projects/${project.id}/burndown/?unit=${unit}`),
  });
  const { data: bt } = useQuery({
    queryKey: ["budget-trend", project.id], queryFn: () => api(`/analytics/projects/${project.id}/budget-trend/`),
  });

  const burn = bd && bd.days.length > 0 && {
    title: { text: "Burndown", left: "center", textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" }, legend: { bottom: 0 },
    xAxis: { type: "category", data: bd.days }, yAxis: { type: "value", name: unit === "hours" ? "Hours left" : "Tasks left", minInterval: 1 },
    series: [
      { name: "Remaining", type: "line", data: bd.remaining, areaStyle: { opacity: 0.12 }, smooth: false },
      { name: "Ideal", type: "line", data: bd.ideal, lineStyle: { type: "dashed" }, symbol: "none" },
      { name: "Scope", type: "line", data: bd.scope, lineStyle: { width: 1 }, symbol: "none" },
    ],
  };
  const budget = bt && bt.weeks.length > 0 && {
    title: { text: "Cost vs budget", left: "center", textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" }, legend: { bottom: 0 },
    xAxis: { type: "category", data: bt.weeks, name: "Week of" }, yAxis: { type: "value", name: "Cost" },
    series: [
      { name: "Cumulative cost", type: "line", data: bt.cumulative_cost, areaStyle: { opacity: 0.12 } },
      ...(bt.budget > 0 ? [{ name: "Budget", type: "line", data: bt.weeks.map(() => bt.budget), lineStyle: { type: "dashed", color: "#dc2626" }, itemStyle: { color: "#dc2626" }, symbol: "none" }] : []),
    ],
  };

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="row"><h2 style={{ flex: 1 }}>Burndown and budget</h2>
        <select aria-label="Burndown unit" value={unit} onChange={(e) => setUnit(e.target.value)}>
          <option value="tasks">By tasks</option><option value="hours">By estimated hours</option>
        </select>
      </div>
      <div className="grid2" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16 }}>
        {burn ? <Chart option={burn} /> : <p className="muted">Add tasks to see the burndown.</p>}
        {budget ? <Chart option={budget} /> : <p className="muted">Log time on this project to see cost against budget.</p>}
      </div>
    </div>
  );
}
