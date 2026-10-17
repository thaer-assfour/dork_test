import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Program } from "../api";

export default function Discovery() {
  const qc = useQueryClient();
  const [status, setStatus] = useState("candidate");
  const [q, setQ] = useState("");
  const [msg, setMsg] = useState("");

  const programs = useQuery({
    queryKey: ["programs", status, q],
    queryFn: () => api.programs(status, q || undefined),
  });

  const discover = useMutation({
    mutationFn: (source: string) => api.discover(source, true),
    onSuccess: (r) => {
      setMsg(`Fetched ${r.fetched}, added ${r.added} new candidates.`);
      qc.invalidateQueries({ queryKey: ["programs"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const setStatusMut = useMutation({
    mutationFn: ({ id, s }: { id: number; s: string }) => api.setProgramStatus(id, s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["programs"] }),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Program Discovery</h1>

      <div className="card mb-4 flex flex-wrap items-center gap-2">
        <span className="text-sm text-slate-400">Import self-hosted candidates:</span>
        <button className="btn-ghost" disabled={discover.isPending} onClick={() => discover.mutate("disclose_io")}>
          disclose.io
        </button>
        <button className="btn-ghost" disabled={discover.isPending} onClick={() => discover.mutate("projectdiscovery")}>
          ProjectDiscovery
        </button>
        <ManualAdd onAdded={() => { setMsg("Manual program added."); qc.invalidateQueries({ queryKey: ["programs"] }); }} />
        {discover.isPending && <span className="text-xs text-slate-400">importing…</span>}
        {msg && <span className="text-xs text-accent">{msg}</span>}
      </div>

      <div className="flex gap-2 mb-3">
        <select className="input max-w-40" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="candidate">Candidates</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
        <input className="input" placeholder="Search by name…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <div className="card overflow-x-auto p-0">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Name</th>
              <th className="th">Source</th>
              <th className="th">Bounty</th>
              <th className="th">Policy</th>
              <th className="th">Actions</th>
            </tr>
          </thead>
          <tbody>
            {programs.data?.map((p) => (
              <ProgramRow key={p.id} p={p} onSet={(s) => setStatusMut.mutate({ id: p.id, s })} />
            ))}
            {programs.data?.length === 0 && (
              <tr><td className="td text-slate-500" colSpan={5}>No programs. Import from a source above.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProgramRow({ p, onSet }: { p: Program; onSet: (s: string) => void }) {
  const bounty =
    p.offers_bounty === true ? <span className="badge bg-green-500/20 text-green-300">bounty</span>
    : p.offers_bounty === false ? <span className="badge bg-slate-500/20 text-slate-300">VDP</span>
    : <span className="badge bg-yellow-500/20 text-yellow-300">unknown</span>;
  return (
    <tr>
      <td className="td font-medium">{p.name}</td>
      <td className="td text-slate-400">{p.source}</td>
      <td className="td">{bounty}</td>
      <td className="td">
        {p.policy_url ? <a className="text-accent hover:underline" href={p.policy_url} target="_blank" rel="noreferrer">policy</a> : "—"}
      </td>
      <td className="td flex gap-1">
        <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => onSet("approved")}>Approve</button>
        <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => onSet("rejected")}>Reject</button>
      </td>
    </tr>
  );
}

function ManualAdd({ onAdded }: { onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [policy, setPolicy] = useState("");
  const add = useMutation({
    mutationFn: () => api.addManual({ name, policy_url: policy }),
    onSuccess: () => { setOpen(false); setName(""); setPolicy(""); onAdded(); },
  });
  if (!open) return <button className="btn-ghost" onClick={() => setOpen(true)}>+ Manual</button>;
  return (
    <span className="flex items-center gap-1">
      <input className="input max-w-36" placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
      <input className="input max-w-56" placeholder="policy url" value={policy} onChange={(e) => setPolicy(e.target.value)} />
      <button className="btn !px-2 !py-1 text-xs" disabled={!name || !policy || add.isPending} onClick={() => add.mutate()}>Save</button>
      <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => setOpen(false)}>×</button>
    </span>
  );
}
