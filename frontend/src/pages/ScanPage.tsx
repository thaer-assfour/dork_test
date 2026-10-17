import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type Estimate } from "../api";

export default function ScanPage() {
  const targets = useQuery({ queryKey: ["targets", true], queryFn: () => api.targets(true) });
  const dorks = useQuery({ queryKey: ["dorks"], queryFn: api.dorks });
  const engines = useQuery({ queryKey: ["engines"], queryFn: api.engines });

  const [selTargets, setSelTargets] = useState<number[]>([]);
  const [selDorks, setSelDorks] = useState<number[]>([]);
  const [engine, setEngine] = useState<string>("");
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [estimating, setEstimating] = useState(false);
  const [runMsg, setRunMsg] = useState("");

  // default engine once loaded
  useEffect(() => {
    if (!engine && engines.data?.length) {
      setEngine(engines.data.find((e) => e.is_default)?.name ?? engines.data[0].name);
    }
  }, [engines.data, engine]);

  // default: select all enabled dorks
  useEffect(() => {
    if (dorks.data && selDorks.length === 0) {
      setSelDorks(dorks.data.filter((d) => d.enabled).map((d) => d.id));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dorks.data]);

  const engineInfo = engines.data?.find((e) => e.name === engine);

  // Live cost estimate: debounced recompute whenever the selection or engine changes.
  useEffect(() => {
    if (!engine || selTargets.length === 0 || selDorks.length === 0) {
      setEstimate(null);
      return;
    }
    setEstimating(true);
    const h = setTimeout(async () => {
      try {
        setEstimate(await api.estimate(selTargets, selDorks, engine));
      } catch {
        setEstimate(null);
      } finally {
        setEstimating(false);
      }
    }, 350);
    return () => clearTimeout(h);
  }, [selTargets, selDorks, engine]);

  const run = useMutation({
    mutationFn: () => api.runScan(selTargets, selDorks, engine),
    onSuccess: (s) => setRunMsg(`Scan #${s.id} started (${s.status}). Check Coverage / Results.`),
    onError: (e: Error) => setRunMsg(e.message),
  });

  const toggle = (arr: number[], set: (v: number[]) => void, id: number) =>
    set(arr.includes(id) ? arr.filter((x) => x !== id) : [...arr, id]);

  const allTargets = targets.data ?? [];
  const canRun = !!engineInfo?.configured && selTargets.length > 0 && selDorks.length > 0 && !run.isPending;

  const costColor = useMemo(() => {
    if (!estimate) return "text-slate-400";
    if (estimate.warn) return "text-red-400";
    return "text-accent";
  }, [estimate]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Run Scan</h1>
      <div className="grid md:grid-cols-3 gap-4">
        {/* targets */}
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold">Approved targets</h2>
            <button className="text-xs text-accent" onClick={() => setSelTargets(allTargets.map((t) => t.id))}>all</button>
          </div>
          <div className="max-h-72 overflow-auto flex flex-col gap-1">
            {allTargets.map((t) => (
              <label key={t.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={selTargets.includes(t.id)} onChange={() => toggle(selTargets, setSelTargets, t.id)} />
                <span className="font-mono">{t.value}</span>
              </label>
            ))}
            {allTargets.length === 0 && <span className="text-xs text-slate-500">Approve targets first.</span>}
          </div>
        </div>

        {/* dorks */}
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold">Dorks</h2>
            <button className="text-xs text-accent" onClick={() => setSelDorks((dorks.data ?? []).map((d) => d.id))}>all</button>
          </div>
          <div className="max-h-72 overflow-auto flex flex-col gap-1">
            {dorks.data?.map((d) => (
              <label key={d.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={selDorks.includes(d.id)} onChange={() => toggle(selDorks, setSelDorks, d.id)} />
                <span>{d.name}</span>
                <span className="text-xs text-slate-500">P{d.priority}</span>
              </label>
            ))}
          </div>
        </div>

        {/* engine + cost */}
        <div className="card flex flex-col gap-3">
          <div>
            <label className="text-xs text-slate-400">Search provider</label>
            <select className="input" value={engine} onChange={(e) => setEngine(e.target.value)}>
              {engines.data?.map((e) => (
                <option key={e.name} value={e.name}>
                  {e.name} — ${e.price_per_1000}/1k {e.configured ? "" : "(no key)"}
                </option>
              ))}
            </select>
            {engineInfo && !engineInfo.configured && (
              <p className="text-xs text-red-400 mt-1">No API key configured for this provider.</p>
            )}
          </div>

          {/* Live cost counter */}
          <div className="rounded-lg bg-ink border border-edge p-3">
            <div className="text-xs text-slate-400 mb-1">
              Estimated cost {estimating && <span className="animate-pulse">· updating…</span>}
            </div>
            <div className={`text-3xl font-bold ${costColor}`}>
              ${estimate ? estimate.estimated_cost.toFixed(2) : "0.00"}
            </div>
            {estimate && (
              <div className="text-xs text-slate-400 mt-2 space-y-0.5">
                <div>Raw queries: {estimate.raw_count}</div>
                <div>After merge: {estimate.merged_count}</div>
                <div>From cache: {estimate.cached_count}</div>
                <div className="text-slate-200">Billable: {estimate.billable_count}</div>
                {estimate.warn && <div className="text-red-400">⚠ Above your cost threshold.</div>}
              </div>
            )}
          </div>

          <button className="btn justify-center" disabled={!canRun} onClick={() => run.mutate()}>
            {run.isPending ? "Running…" : "Start scan"}
          </button>
          {runMsg && <p className="text-xs text-accent">{runMsg}</p>}
        </div>
      </div>
    </div>
  );
}
