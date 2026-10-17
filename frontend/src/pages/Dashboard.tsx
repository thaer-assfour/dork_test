import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

const tiles: { key: string; label: string }[] = [
  { key: "programs_total", label: "Programs found" },
  { key: "programs_approved", label: "Programs approved" },
  { key: "targets_approved", label: "Targets approved" },
  { key: "dorks_enabled", label: "Dorks enabled" },
  { key: "scans_total", label: "Scans run" },
  { key: "results_new", label: "New results" },
];

export default function Dashboard() {
  const { data } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard, refetchInterval: 5000 });
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {tiles.map((t) => (
          <div key={t.key} className="card">
            <div className="text-3xl font-bold text-accent">{data?.[t.key] ?? "—"}</div>
            <div className="text-sm text-slate-400 mt-1">{t.label}</div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-500 mt-6">
        Only run dorks against targets you are authorized to test. DorkHub refuses to scan
        unapproved targets, and never visits or interacts with results — that stays a manual step
        inside each program's scope.
      </p>
    </div>
  );
}
