import { useQuery } from "@tanstack/react-query";
import { api } from "../api.js";

export default function Audit() {
  const { data = [], isLoading } = useQuery({ queryKey: ["audit"], queryFn: () => api("/analytics/audit/?limit=100") });
  return (
    <>
      <h1>Audit Log</h1>
      <div className="sub">Every create, update and delete on projects and tasks, with who made it</div>
      <div className="card">
        {isLoading ? <p>Loading...</p> : (
          <table>
            <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Entity</th><th>Name</th></tr></thead>
            <tbody>
              {data.map((e, i) => (
                <tr key={i}>
                  <td>{new Date(e.at).toLocaleString()}</td><td>{e.by || "system"}</td>
                  <td><span className="badge">{e.action}</span></td><td>{e.entity} #{e.entity_id}</td><td>{e.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
