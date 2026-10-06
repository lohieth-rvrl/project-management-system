import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import usePaged from "../components/usePaged.js";
import Pagination from "../components/Pagination.jsx";

export default function Notifications() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const p = usePaged("notifications", `/notifications/${unreadOnly ? "?unread=1" : ""}`);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["notifications"] }); qc.invalidateQueries({ queryKey: ["unread"] }); };
  const markAll = useMutation({ mutationFn: () => api("/notifications/mark-all-read/", { method: "POST" }), onSuccess: refresh });

  const open = async (n) => {
    if (!n.read_at) { await api(`/notifications/${n.id}/read/`, { method: "POST" }); refresh(); }
    if (n.link) nav(n.link);
  };

  return (
    <>
      <h1>Notifications</h1>
      <div className="sub">Assignments, comments, mentions, approvals, risks and due dates</div>
      <div className="card">
        <div className="row" style={{ marginBottom: 8 }}>
          <label><input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} /> Unread only</label>
          <button onClick={() => markAll.mutate()}>Mark all as read</button>
        </div>
        {p.isLoading ? <p>Loading...</p> : p.rows.length === 0 ? <p className="muted">Nothing here.</p> : (
          <table>
            <tbody>
              {p.rows.map((n) => (
                <tr key={n.id} onClick={() => open(n)} style={{ cursor: "pointer", fontWeight: n.read_at ? 400 : 600 }}>
                  <td><span className="badge">{n.kind}</span></td>
                  <td>{n.title}<div className="muted" style={{ fontWeight: 400 }}>{n.body}</div></td>
                  <td>{new Date(n.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <Pagination page={p.page} pageSize={p.pageSize} count={p.count} onPage={p.setPage} onPageSize={p.setPageSize} />
      </div>
    </>
  );
}
