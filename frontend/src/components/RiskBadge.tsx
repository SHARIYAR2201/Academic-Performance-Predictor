const STYLES: Record<string, string> = {
  LOW: "bg-emerald-50 text-emerald-700 border-emerald-200",
  MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
  HIGH: "bg-red-50 text-red-700 border-red-200",
};

export function RiskBadge({ level }: { level: "LOW" | "MEDIUM" | "HIGH" }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${STYLES[level]}`}>
      {level} RISK
    </span>
  );
}
