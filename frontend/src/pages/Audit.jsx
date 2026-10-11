import { useState } from "react";
import usePaged from "../components/usePaged.js";
import Pagination from "../components/Pagination.jsx";

const ENTITIES = ["Task", "Project", "Sprint", "Milestone", "Member", "Risk", "Timesheet", "User"];

export default function Audit() {
  const [entity, setEntity] = useState("");
  const [action, setAction] = useState("");
  const [user, setUser] = useState("");
  const qs = new URLSearchParams({ ...(entity && { entity }), ...(action && { action }), ...(user.trim() && { user: user.trim() }) }).toString();
  const p = usePaged("audit", `/analytics/audit/${qs ? `?${qs}` : ""}`);

  return (
    <>
      <h1>Audit Log</h1>
      <div className="sub">Every create, update and delete across projects, tasks, sprints, milestones, members, risks, timesheets and people</div>
      <div className="card">
        <div className="row" style={{ marginBottom: 8 }}>
          <select aria-label="Filter by type" value={entity} onChange={(e) => setEntity(e.target.value)}>
            <option value="">All types</option>{ENTITIES.map((x) => <option key={x}>{x}</option>)}
          </select>
          <select aria-label="Filter by action" value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">All actions</option><option>created</option><option>updated</option><option>deleted</option>
          </select>
          <input aria-label="Filter by person" placeholder="Username" value={user} onChange={(e) => setUser(e.target.value)} />
        </div>
        {p.isLoading ? <p>Loading...</p> : (
          <table>
            <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Entity</th><th>Name</th></tr></thead>
            <tbody>
              {p.rows.map((e, i) => (
                <tr key={`${e.entity}-${e.entity_id}-${e.at}-${i}`}>
                  <td>{new Date(e.at).toLocaleString()}</td><td>{e.by || "system"}</td>
                  <td><span className="badge">{e.action}</span></td><td>{e.entity} #{e.entity_id}</td><td>{e.name}</td>
                </tr>
              ))}
              {p.rows.length === 0 && <tr><td colSpan={5} className="muted">No matching changes.</td></tr>}
            </tbody>
          </table>
        )}
        <Pagination page={p.page} pageSize={p.pageSize} count={p.count} onPage={p.setPage} onPageSize={p.setPageSize} />
      </div>
    </>
  );
}
