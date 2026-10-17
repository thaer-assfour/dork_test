import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type AiSettingsIn } from "../api";

export default function Settings() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });

  const [form, setForm] = useState<AiSettingsIn>({});
  const [apiKey, setApiKey] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (settings.data) {
      const a = settings.data.ai;
      setForm({
        enabled: a.enabled,
        provider: a.provider,
        base_url: a.base_url,
        model: a.model,
        max_tokens: a.max_tokens,
      });
    }
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () =>
      api.updateAiSettings({ ...form, api_key: apiKey || "" }),
    onSuccess: () => {
      setMsg("Saved.");
      setApiKey("");
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const test = useMutation({
    mutationFn: api.aiTest,
    onSuccess: (r) => setMsg(r.ok ? `Connection OK: "${r.reply}"` : `Reply: "${r.reply}"`),
    onError: (e: Error) => setMsg(`Test failed: ${e.message}`),
  });

  const clearKey = useMutation({
    mutationFn: () => api.updateAiSettings({ api_key: "__CLEAR__" }),
    onSuccess: () => { setMsg("API key cleared."); qc.invalidateQueries({ queryKey: ["settings"] }); },
  });

  const cfg = settings.data?.ai;
  const catalog = settings.data?.model_catalog ?? {};
  const provider = form.provider ?? "openai_compatible";
  const models = catalog[provider] ?? [];

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-4">Settings</h1>

      <div className="card flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold">AI assistance</h2>
            <p className="text-xs text-slate-400">Optional. Off by default. Used only on demand.</p>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!form.enabled}
              onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
            />
            Enabled
          </label>
        </div>

        <div>
          <label className="text-xs text-slate-400">Provider</label>
          <select
            className="input"
            value={provider}
            onChange={(e) => setForm({ ...form, provider: e.target.value })}
          >
            <option value="openai_compatible">Local / OpenAI-compatible (Ollama, OpenRouter, Groq…)</option>
            <option value="anthropic">Anthropic API (needs API billing, not a Pro plan)</option>
          </select>
        </div>

        {provider === "openai_compatible" && (
          <div>
            <label className="text-xs text-slate-400">Base URL</label>
            <input
              className="input"
              placeholder="http://localhost:11434/v1"
              value={form.base_url ?? ""}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
            />
            <p className="text-xs text-slate-500 mt-1">
              Local Ollama default shown. For a hosted gateway, use its /v1 URL.
            </p>
          </div>
        )}

        <div>
          <label className="text-xs text-slate-400">Model</label>
          <input
            className="input"
            list="model-list"
            value={form.model ?? ""}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
          />
          <datalist id="model-list">
            {models.map((m) => <option key={m} value={m} />)}
          </datalist>
        </div>

        <div>
          <label className="text-xs text-slate-400">
            API key {cfg?.has_key && <span className="text-green-400">(a key is saved)</span>}
          </label>
          <div className="flex gap-2">
            <input
              className="input"
              type="password"
              placeholder={cfg?.has_key ? "•••••• (leave blank to keep)" : "Paste key (not needed for local Ollama)"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            {cfg?.has_key && (
              <button className="btn-ghost text-red-300" onClick={() => clearKey.mutate()}>Clear</button>
            )}
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-400">Max tokens per call</label>
          <input
            className="input max-w-40"
            type="number"
            value={form.max_tokens ?? 1024}
            onChange={(e) => setForm({ ...form, max_tokens: Number(e.target.value) })}
          />
        </div>

        <div className="flex items-center gap-2">
          <button className="btn" disabled={save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? "Saving…" : "Save"}
          </button>
          <button className="btn-ghost" disabled={test.isPending} onClick={() => test.mutate()}>
            {test.isPending ? "Testing…" : "Test connection"}
          </button>
          {msg && <span className="text-xs text-accent">{msg}</span>}
        </div>
      </div>

      <p className="text-xs text-slate-500 mt-4">
        A Claude Pro/Max subscription does not include API access — those are billed separately.
        For a free, private, self-hosted option, run a local model with Ollama and point the base
        URL at it. The key is stored encrypted in the database.
      </p>
    </div>
  );
}
