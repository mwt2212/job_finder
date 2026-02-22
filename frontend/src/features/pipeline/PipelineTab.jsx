export default function PipelineTab({ active, children }) {
  if (!active) return null;
  return children;
}
