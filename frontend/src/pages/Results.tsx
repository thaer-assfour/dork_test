import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";

const LABELS = ["new", "reviewing", "interesting", "false_positive", "reported"];
const labelColor: Record<string, string> = {
  new: "bg-accent/20 text-accent",
  reviewing: "bg-yellow-500/20 text-yellow-300",
  interesting: "bg-green-500/20 text-green-300",
  false_positive: "bg-slate-500/20 text-slate-300",
  reported: "bg-purple-500/20 text-purple-300",
};

export default function Results() {
  const qc = useQueryClient();
  const [label, setLabel] = useState("");
  const results = useQuery({
    queryKey: ["results", label],
    queryFn: () => api.results(undefined, label || undefined),
    refetchInterval: 5000,
  });

  const setLbl = useMutation({
    mutationFn: ({ id, l }: { id: number; l: string }) => api.labelResult(id, l),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["results"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Results</h1>
        <div className="flex gap-2">
          <select className="input max-w-44" value={label} onChange={(e) => setLabel(e.target.value)}>
            <option value="">All labels</option>
            {LABELS.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
          <a className="btn-ghost" href="/api/results/export?fmt=csv">Export CSV</a>
          <a className="btn-ghost" href="/api/results/export?fmt=json">Export JSON</a>
        </div>
      </div>

      <div className="card overflow-x-auto p-0">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">URL</th>
              <th className="th">Title</th>
              <th className="th">Seen</th>
              <th className="th">Label</th>
            </tr>
          </thead>
          <tbody>
            {results.data?.map((r) => (
              <tr key={r.id}>
                <td className="td max-w-md truncate">
                  <a className="text-accent hover:underline" href={r.url} target="_blank" rel="noreferrer">{r.url}</a>
                </td>
                <td className="td max-w-xs truncate text-slate-300">{r.title || "—"}</td>
                <td className="td text-slate-400">{r.seen_count}×</td>
                <td className="td">
                  <select
                    className={`badge ${labelColor[r.label] ?? ""} bg-transparent border border-edge`}
                    value={r.label}
                    onChange={(e) => setLbl.mutate({ id: r.id, l: e.target.value })}
                  >
                    {LABELS.map((l) => <option key={l} value={l}>{l}</option>)}
                  </select>
                </td>
              </tr>
            ))}
            {results.data?.length === 0 && (
              <tr><td className="td text-slate-500" colSpan={4}>No results yet. Run a scan.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
