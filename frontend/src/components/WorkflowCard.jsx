import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api.js";

const STATUSES = [["todo", "To Do"], ["in_progress", "In Progress"], ["review", "In Review"], ["blocked", "Blocked"], ["done", "Done"]];

// rules: null (anything goes) or { from: [to, ...] }. A status missing from the map is unrestricted.
const fullMatrix = () => Object.fromEntries(STATUSES.map(([a]) => [a, STATUSES.map(([b]) => b).filter((b) => b !== a)]));

export default function WorkflowCard({ project, canEdit }) {
  const qc = useQueryClient();
  const [rules, setRules] = useState(project.workflow_transitions);
  const [approval, setApproval] = useState(project.done_requires_approval);
  const [msg, setMsg] = useState("");
  useEffect(() => { setRules(project.workflow_transitions); setApproval(project.done_requires_approval); }, [project]);

  const save = useMutation({
    mutationFn: () => api(`/projects/${project.id}/`, {
      method: "PATCH", body: { workflow_transitions: rules, done_requires_approval: approval },
    }),
    onSuccess: () => { setMsg("Saved"); qc.invalidateQueries({ queryKey: ["project", project.id] }); },
    onError: (e) => setMsg(e.message),
  });

  const has = (a, b) => (rules[a] ? rules[a].includes(b) : true);
  const toggle = (a, b) => {
    const cur = rules[a] || fullMatrix()[a];
    setRules({ ...rules, [a]: cur.includes(b) ? cur.filter((x) => x !== b) : [...cur, b] });
    setMsg("");
  };

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h2>Workflow</h2>
      <p className="muted">Control which status changes are allowed on this project's tasks.</p>
      <label>
        <input type="checkbox" checked={approval} disabled={!canEdit}
          onChange={(e) => { setApproval(e.target.checked); setMsg(""); }} />
        {" "}Only a lead, manager or admin can mark a task Done
      </label>
      {rules === null ? (
        <p>Any status change is allowed. {canEdit && <button type="button" onClick={() => setRules(fullMatrix())}>Customise transitions</button>}</p>
      ) : (
        <>
          <table aria-label="Allowed transitions">
            <thead><tr><th>From \ To</th>{STATUSES.map(([k, l]) => <th key={k}>{l}</th>)}</tr></thead>
            <tbody>
              {STATUSES.map(([a, la]) => (
                <tr key={a}>
                  <td>{la}</td>
                  {STATUSES.map(([b, lb]) => (
                    <td key={b}>{a === b ? "-" : (
                      <input type="checkbox" aria-label={`${la} to ${lb}`} checked={has(a, b)} disabled={!canEdit} onChange={() => toggle(a, b)} />
                    )}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {canEdit && <button type="button" onClick={() => setRules(null)}>Allow any change</button>}
        </>
      )}
      {canEdit && <div className="row" style={{ marginTop: 8 }}>
        <button type="button" onClick={() => save.mutate()} disabled={save.isPending}>Save workflow</button>
        {msg && <span className={msg === "Saved" ? "" : "error"}>{msg}</span>}
      </div>}
    </div>
  );
}
