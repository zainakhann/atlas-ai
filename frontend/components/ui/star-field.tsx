export function StarField() {
  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 opacity-0 dark:opacity-[0.35]"
      style={{
        backgroundImage:
          "radial-gradient(1px 1px at 20% 30%, white, transparent), radial-gradient(1px 1px at 70% 15%, white, transparent), radial-gradient(1px 1px at 40% 60%, white, transparent), radial-gradient(1px 1px at 85% 70%, white, transparent), radial-gradient(1px 1px at 10% 80%, white, transparent), radial-gradient(1px 1px at 60% 40%, white, transparent), radial-gradient(1px 1px at 25% 90%, white, transparent), radial-gradient(1px 1px at 90% 25%, white, transparent), radial-gradient(1px 1px at 50% 10%, white, transparent)",
        backgroundSize: "600px 600px",
      }}
    />
  );
}