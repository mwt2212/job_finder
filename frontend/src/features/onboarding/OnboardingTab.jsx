export default function OnboardingTab({ active, children }) {
  if (!active) return null;
  return children;
}
