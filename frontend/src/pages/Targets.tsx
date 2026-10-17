import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";

export default function Targets() {
  const qc = useQueryClient();
  const targets = useQuery({ queryKey: ["targets"], queryFn: () => api.targets() });
  const [value, setValue] = useState("");
  const [kind, setKind] = useState("domain");

  const create = useMutation({
    mutationFn: () => api.createTarget({ value, kind, approved: true }),
    onSuccess: () => { setValue(""); qc.invalidateQueries({ queryKey: ["targets"] }); },
  });
  const approve = useMutation({
    mutationFn: ({ id, a }: { id: number; a: boolean }) => api.approveTarget(id, a),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["targets"] }),
  });
  const del = useMutation({
    mutationFn: (id: number) => api.deleteTarget(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["targets"] }),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Targets</h1>
      <div className="card mb-4 flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-48">
          <label className="text-xs text-slate-400">Value (domain / wildcard / url)</label>
          <input className="input" placeholder="example.com" value={value} onChange={(e) => setValue(e.target.value)} />
        </div>
        <select className="input max-w-40" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="domain">domain</option>
          <option value="wildcard">wildcard</option>
          <option value="url">url</option>
          <option value="ip_range">ip_range</option>
        </select>
        <button className="btn" disabled={!value || create.isPending} onClick={() => create.mutate()}>Add target</button>
      </div>

      <div className="card overflow-x-auto p-0">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Value</th>
              <th className="th">Kind</th>
              <th className="th">Approved</th>
              <th className="th">Actions</th>
            </tr>
          </thead>
          <tbody>
            {targets.data?.map((t) => (
              <tr key={t.id}>
                <td className="td font-mono">{t.value}</td>
                <td className="td text-slate-400">{t.kind}</td>
                <td className="td">
                  {t.approved
                    ? <span className="badge bg-green-500/20 text-green-300">approved</span>
                    : <span className="badge bg-slate-500/20 text-slate-300">no</span>}
                </td>
                <td className="td flex gap-1">
                  <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => approve.mutate({ id: t.id, a: !t.approved })}>
                    {t.approved ? "Unapprove" : "Approve"}
                  </button>
                  <button className="btn-ghost !px-2 !py-1 text-xs text-red-300" onClick={() => del.mutate(t.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {targets.data?.length === 0 && (
              <tr><td className="td text-slate-500" colSpan={4}>No targets yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
