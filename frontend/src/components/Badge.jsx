export const label = (s) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export default function Badge({ value }) {
  return <span className={`badge ${value}`}>{label(value)}</span>;
}
