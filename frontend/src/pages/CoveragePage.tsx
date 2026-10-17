import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export default function CoveragePage() {
  const cov = useQuery({ queryKey: ["coverage"], queryFn: api.coverage, refetchInterval: 4000 });
  const data = cov.data;

  const cellMap = new Map<string, { last: string | null; count: number }>();
  for (const c of data?.cells ?? []) {
    cellMap.set(`${c.target_id}:${c.dork_id}`, { last: c.last_scanned, count: c.result_count });
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Coverage Matrix</h1>
      <p className="text-sm text-slate-400 mb-3">
        Which dork has been run against which target, and how many results it returned.
      </p>
      <div className="card overflow-auto p-0">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th sticky left-0 bg-panel">Target \ Dork</th>
              {data?.dorks.map((d) => (
                <th key={d.id} className="th whitespace-nowrap" title={d.category}>{d.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.targets.map((t) => (
              <tr key={t.id}>
                <td className="td font-mono sticky left-0 bg-panel">{t.value}</td>
                {data.dorks.map((d) => {
                  const cell = cellMap.get(`${t.id}:${d.id}`);
                  return (
                    <td key={d.id} className="td text-center">
                      {cell ? (
                        <span
                          className={`badge ${cell.count > 0 ? "bg-green-500/20 text-green-300" : "bg-slate-600/30 text-slate-400"}`}
                          title={cell.last ? `scanned ${new Date(cell.last).toLocaleString()}` : ""}
                        >
                          {cell.count}
                        </span>
                      ) : (
                        <span className="text-slate-600">·</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
            {data?.targets.length === 0 && (
              <tr><td className="td text-slate-500">No approved targets.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500 mt-3">
        Green = results found · grey = scanned, nothing found · dot = not scanned yet.
      </p>
    </div>
  );
}
