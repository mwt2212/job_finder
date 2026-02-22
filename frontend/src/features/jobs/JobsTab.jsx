export default function JobsTab({ active, children }) {
  if (!active) return null;
  return children;
}
