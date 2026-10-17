import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import Login from "./components/Login";
import Dashboard from "./pages/Dashboard";
import Discovery from "./pages/Discovery";
import Targets from "./pages/Targets";
import Dorks from "./pages/Dorks";
import ScanPage from "./pages/ScanPage";
import CoveragePage from "./pages/CoveragePage";
import Results from "./pages/Results";
import Settings from "./pages/Settings";

const nav = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/discovery", label: "Discovery" },
  { to: "/targets", label: "Targets" },
  { to: "/dorks", label: "Dork Library" },
  { to: "/scan", label: "Run Scan" },
  { to: "/coverage", label: "Coverage" },
  { to: "/results", label: "Results" },
  { to: "/settings", label: "Settings" },
];

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  // Probe auth: a protected call tells us whether we're in.
  const probe = useQuery({
    queryKey: ["probe"],
    queryFn: async () => {
      try {
        await api.dashboard();
        setAuthed(true);
        return true;
      } catch {
        setAuthed(false);
        return false;
      }
    },
  });

  if (probe.isLoading && authed === null) {
    return <div className="p-8 text-slate-400">Loading…</div>;
  }
  if (authed === false) {
    return <Login onSuccess={() => setAuthed(true)} />;
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 shrink-0 border-r border-edge bg-panel/50 p-4 flex flex-col gap-1">
        <div className="text-xl font-bold mb-4 px-2">
          Dork<span className="text-accent">Hub</span>
        </div>
        {nav.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) =>
              `px-3 py-2 rounded-lg text-sm ${
                isActive ? "bg-accent/20 text-white" : "text-slate-300 hover:bg-edge/40"
              }`
            }
          >
            {n.label}
          </NavLink>
        ))}
        <button
          className="btn-ghost mt-auto"
          onClick={async () => {
            await api.logout();
            setAuthed(false);
          }}
        >
          Logout
        </button>
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/discovery" element={<Discovery />} />
          <Route path="/targets" element={<Targets />} />
          <Route path="/dorks" element={<Dorks />} />
          <Route path="/scan" element={<ScanPage />} />
          <Route path="/coverage" element={<CoveragePage />} />
          <Route path="/results" element={<Results />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
