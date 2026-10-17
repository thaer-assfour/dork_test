import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Dork } from "../api";

export default function Dorks() {
  const qc = useQueryClient();
  const dorks = useQuery({ queryKey: ["dorks"], queryFn: api.dorks });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) => api.toggleDork(id, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dorks"] }),
  });
  const importMut = useMutation({
    mutationFn: api.importDorks,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dorks"] }),
  });

  const byCat: Record<string, Dork[]> = {};
  for (const d of dorks.data ?? []) (byCat[d.category] ??= []).push(d);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Dork Library</h1>
        <button className="btn-ghost" disabled={importMut.isPending} onClick={() => importMut.mutate()}>
          Re-import from YAML
        </button>
      </div>

      {Object.entries(byCat).map(([cat, items]) => (
        <div key={cat} className="card mb-3">
          <div className="text-sm uppercase tracking-wide text-slate-400 mb-2">{cat}</div>
          <table className="w-full">
            <tbody>
              {items.map((d) => (
                <tr key={d.id}>
                  <td className="td w-8">
                    <input type="checkbox" checked={d.enabled} onChange={() => toggle.mutate({ id: d.id, enabled: !d.enabled })} />
                  </td>
                  <td className="td font-medium w-40">{d.name}</td>
                  <td className="td font-mono text-xs text-slate-300">{d.template}</td>
                  <td className="td w-20">
                    <span className={`badge ${d.priority === 1 ? "bg-red-500/20 text-red-300" : d.priority === 2 ? "bg-yellow-500/20 text-yellow-300" : "bg-slate-500/20 text-slate-300"}`}>
                      P{d.priority}
                    </span>
                  </td>
                  <td className="td w-24">{d.mergeable && <span className="badge bg-accent/20 text-accent">merge</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {dorks.data?.length === 0 && (
        <div className="card text-slate-500">No dorks. Click "Re-import from YAML".</div>
      )}
    </div>
  );
}
