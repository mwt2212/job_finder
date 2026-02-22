export default function SettingsTab({ active, children }) {
  if (!active) return null;
  return children;
}
