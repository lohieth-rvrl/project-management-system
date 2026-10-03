import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api.js";
import Pagination from "../components/Pagination.jsx";

export default function Audit() {
  const { data = [], isLoading } = useQuery({ queryKey: ["audit"], queryFn: () => api("/analytics/audit/?limit=200") });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // The audit endpoint returns one merged list, so it is paged here in the browser.
  const lastPage = Math.max(1, Math.ceil(data.length / pageSize));
  const current = Math.min(page, lastPage);
  const rows = data.slice((current - 1) * pageSize, current * pageSize);

  return (
    <>
      <h1>Audit Log</h1>
      <div className="sub">Every create, update and delete on projects and tasks, with who made it (latest 200 changes)</div>
      <div className="card">
        {isLoading ? <p>Loading...</p> : (
          <table>
            <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Entity</th><th>Name</th></tr></thead>
            <tbody>
              {rows.map((e, i) => (
                <tr key={`${e.entity}-${e.entity_id}-${e.at}-${i}`}>
                  <td>{new Date(e.at).toLocaleString()}</td><td>{e.by || "system"}</td>
                  <td><span className="badge">{e.action}</span></td><td>{e.entity} #{e.entity_id}</td><td>{e.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <Pagination page={current} pageSize={pageSize} count={data.length} onPage={setPage}
          onPageSize={(n) => { setPageSize(n); setPage(1); }} />
      </div>
    </>
  );
}
