import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const GROUPS = [
  ["projects", "Projects", (r) => `/projects/${r.id}`],
  ["tasks", "Tasks", (r) => `/tasks?task=${r.id}`],
  ["risks", "Risks", () => "/risks"],
  ["people", "People", () => "/users"],
];

export default function SearchBox() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const text = q.trim();
    if (text.length < 2) { setRes(null); return undefined; }
    let stale = false; // ignore a slow answer to an older query
    const t = setTimeout(() => {
      api(`/analytics/search/?q=${encodeURIComponent(text)}`)
        .then((d) => { if (!stale) setRes(d); })
        .catch(() => { if (!stale) setRes(null); });
    }, 250);
    return () => { stale = true; clearTimeout(t); };
  }, [q]);

  const go = (path) => { setOpen(false); setQ(""); setRes(null); nav(path); };
  const total = res ? GROUPS.reduce((n, [k]) => n + res[k].length, 0) : 0;

  return (
    <div className="search">
      <input placeholder="Search..." value={q} aria-label="Search"
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)} />
      {open && res && (
        <div className="search-results">
          {total === 0 && <div className="muted" style={{ padding: 8 }}>No results</div>}
          {GROUPS.map(([key, title, href]) => res[key].length > 0 && (
            <div key={key}>
              <div className="search-group">{title}</div>
              {res[key].map((r) => (
                <button key={`${key}-${r.id}`} className="search-item" onMouseDown={() => go(href(r))}>
                  <span>{r.label}</span><small>{r.sub}</small>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
