export const PAGE_SIZES = [10, 25, 50, 100];

// Server-driven pager. `count` is the total number of rows across all pages.
export default function Pagination({ page, pageSize, count, onPage, onPageSize }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  const from = count === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, count);

  return (
    <div className="pager">
      <span className="muted">{from}-{to} of {count}</span>
      <span className="pager-ctl">
        <select value={pageSize} onChange={(e) => onPageSize(Number(e.target.value))} aria-label="Rows per page">
          {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} / page</option>)}
        </select>
        <button className="ghost" disabled={page <= 1} onClick={() => onPage(1)}>First</button>
        <button className="ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>Prev</button>
        <span>Page {page} of {pages}</span>
        <button className="ghost" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
        <button className="ghost" disabled={page >= pages} onClick={() => onPage(pages)}>Last</button>
      </span>
    </div>
  );
}
