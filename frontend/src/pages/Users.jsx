import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useOutletContext } from "react-router-dom";
import { api } from "../api.js";
import Pagination from "../components/Pagination.jsx";
import usePaged from "../components/usePaged.js";
import { label } from "../components/Badge.jsx";

const ROLES = ["admin", "manager", "lead", "member", "viewer"];
const blank = { username: "", first_name: "", last_name: "", email: "", role: "member", weekly_capacity_hours: 40, is_active: true, password: "" };

export default function Users() {
  const { me } = useOutletContext();
  const qc = useQueryClient();
  const isAdmin = me?.role === "admin";
  const canManage = me && ["admin", "manager"].includes(me.role);
  const [search, setSearch] = useState("");
  const pg = usePaged("users", `/users/?ordering=username${search ? `&search=${encodeURIComponent(search)}` : ""}`);
  const [editing, setEditing] = useState(null); // null = closed, {} = new, user = edit
  const [form, setForm] = useState(blank);
  const [error, setError] = useState("");

  const roles = isAdmin ? ROLES : ROLES.filter((r) => r !== "admin");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const refresh = () => qc.invalidateQueries({ queryKey: ["users"] });

  const openNew = () => { setForm(blank); setEditing({}); setError(""); };
  const openEdit = (u) => { setForm({ ...blank, ...u, password: "" }); setEditing(u); setError(""); };

  const save = useMutation({
    mutationFn: () => {
      const body = { ...form };
      if (!body.password) delete body.password;
      delete body.id; delete body.full_name;
      return editing.id
        ? api(`/users/${editing.id}/`, { method: "PATCH", body })
        : api("/users/", { method: "POST", body });
    },
    onSuccess: () => { refresh(); setEditing(null); },
    onError: (e) => setError(e.message),
  });
  const remove = useMutation({
    mutationFn: (id) => api(`/users/${id}/`, { method: "DELETE" }),
    onSuccess: refresh,
    onError: (e) => setError(e.message),
  });

  // A manager cannot touch admin accounts, and nobody edits their own role from here
  const locked = (u) => u.role === "admin" && !isAdmin;

  return (
    <>
      <div className="toolbar">
        <div><h1>People</h1><div className="sub">{canManage ? "Add people, change roles, deactivate accounts" : "Everyone on the platform"}</div></div>
        <div className="row">
          <input placeholder="Filter by name" value={search} onChange={(e) => setSearch(e.target.value)} style={{ width: 200 }} />
          {canManage && <button onClick={openNew}>Add person</button>}
        </div>
      </div>
      {error && !editing && <div className="error">{error}</div>}

      {editing && (
        <form className="card form" style={{ marginBottom: 16 }} onSubmit={(e) => { e.preventDefault(); setError(""); save.mutate(); }}>
          <div><label>Username</label><input value={form.username} onChange={set("username")} required disabled={!!editing.id} /></div>
          <div><label>First name</label><input value={form.first_name} onChange={set("first_name")} /></div>
          <div><label>Last name</label><input value={form.last_name} onChange={set("last_name")} /></div>
          <div><label>Email</label><input type="email" value={form.email} onChange={set("email")} /></div>
          <div><label>Role</label>
            <select value={form.role} onChange={set("role")} disabled={editing.id === me.id}>
              {roles.map((r) => <option key={r} value={r}>{label(r)}</option>)}
            </select></div>
          <div><label>Weekly hours</label><input type="number" min="0" max="80" value={form.weekly_capacity_hours} onChange={set("weekly_capacity_hours")} /></div>
          <div><label>{editing.id ? "New password (optional)" : "Password"}</label>
            <input type="password" value={form.password} onChange={set("password")} minLength={8} required={!editing.id} autoComplete="new-password" /></div>
          <div><label>Active</label><input type="checkbox" checked={form.is_active} onChange={set("is_active")} disabled={editing.id === me.id} style={{ width: "auto" }} /></div>
          <div className="row"><button disabled={save.isPending}>Save</button><button type="button" className="ghost" onClick={() => setEditing(null)}>Cancel</button></div>
          {error && <div className="error" style={{ gridColumn: "1 / -1" }}>{error}</div>}
        </form>
      )}

      <div className="card">
        <table>
          <thead><tr><th>Username</th><th>Name</th><th>Email</th><th>Role</th><th>Hours/week</th><th>Status</th>{canManage && <th></th>}</tr></thead>
          <tbody>
            {pg.rows.map((u) => (
              <tr key={u.id} style={{ opacity: u.is_active ? 1 : 0.55 }}>
                <td><b>{u.username}</b></td><td>{u.full_name}</td><td>{u.email || "-"}</td>
                <td><span className="badge">{label(u.role)}</span></td><td>{u.weekly_capacity_hours}</td>
                <td>{u.is_active ? "Active" : "Deactivated"}</td>
                {canManage && (
                  <td className="row">
                    <button className="ghost" disabled={locked(u)} onClick={() => openEdit(u)}>Edit</button>
                    <button className="ghost danger" disabled={locked(u) || u.id === me.id}
                      onClick={() => window.confirm(`Delete ${u.username}? Their tasks become unassigned. Deactivating is safer.`) && remove.mutate(u.id)}>Delete</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={pg.page} pageSize={pg.pageSize} count={pg.count} onPage={pg.setPage} onPageSize={pg.setPageSize} />
      </div>
    </>
  );
}
