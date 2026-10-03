import { Navigate, NavLink, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, auth } from "./api.js";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Projects from "./pages/Projects.jsx";
import Board from "./pages/Board.jsx";
import Timesheet from "./pages/Timesheet.jsx";
import Risks from "./pages/Risks.jsx";
import Team from "./pages/Team.jsx";
import Audit from "./pages/Audit.jsx";

function Shell() {
  const nav = useNavigate();
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api("/users/me/") });

  const logout = () => { auth.clear(); nav("/login"); };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo">Project Management</div>
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/projects">Projects</NavLink>
        <NavLink to="/board">Task Board</NavLink>
        <NavLink to="/timesheet">Timesheet</NavLink>
        <NavLink to="/risks">Risks</NavLink>
        <NavLink to="/team">Team Workload</NavLink>
        <NavLink to="/audit">Audit Log</NavLink>
        {me && (
          <div className="user">
            Signed in as <b>{me.username}</b><br />Role: {me.role}
          </div>
        )}
        <button className="sidebar-btn" onClick={logout}>Sign out</button>
      </aside>
      <main className="main"><Outlet context={{ me }} /></main>
    </div>
  );
}

function Protected({ children }) {
  return auth.access ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected><Shell /></Protected>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/board" element={<Board />} />
        <Route path="/timesheet" element={<Timesheet />} />
        <Route path="/risks" element={<Risks />} />
        <Route path="/team" element={<Team />} />
        <Route path="/audit" element={<Audit />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
