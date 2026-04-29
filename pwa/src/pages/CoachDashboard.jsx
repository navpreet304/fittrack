import React, { useEffect, useState } from "react";
import { useAuth } from "../AuthContext";
import { getCoachDashboard, getCoachClientProgress, downloadCoachReport } from "../api";
import Toast from "../components/Toast";

export default function CoachDashboard() {
  const { auth, baseUrl } = useAuth();
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientProgress, setClientProgress] = useState(null);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState("");
  const [downloading, setDownloading] = useState("");

  async function load(q) {
    try {
      const data = await getCoachDashboard(baseUrl, auth.token, q);
      setClients(Array.isArray(data) ? data : (data.clients || []));
    } catch (err) {
      setToast(err.message);
    }
  }

  useEffect(() => { load(""); }, []);

  async function viewProgress(client) {
    setSelectedClient(client);
    setClientProgress(null);
    try {
      const prog = await getCoachClientProgress(baseUrl, auth.token, client.id || client.user_id);
      setClientProgress(prog);
    } catch (err) {
      setToast(err.message);
    }
  }

  async function handleDownload(fmt) {
    if (!selectedClient) return;
    setDownloading(fmt);
    try {
      await downloadCoachReport(baseUrl, auth.token, selectedClient.id, fmt);
    } catch (err) {
      setToast(err.message);
    } finally {
      setDownloading("");
    }
  }

  return (
    <div style={{ padding: "1.5rem", color: "#fff" }}>
      <Toast message={toast} onClose={() => setToast("")} />
      <h2 style={{ margin: "0 0 1.5rem", fontSize: "1.4rem", fontWeight: 700 }}>Coach Dashboard</h2>

      <input
        placeholder="Search clients…"
        value={search}
        onChange={(e) => { setSearch(e.target.value); load(e.target.value); }}
        style={{ ...inputStyle, maxWidth: "320px", marginBottom: "1rem" }}
      />

      <div style={{ display: "flex", gap: "1.5rem" }}>
        {/* Client list */}
        <div style={{ ...cardStyle, flex: "0 0 280px" }}>
          <h3 style={{ margin: "0 0 0.75rem", fontSize: "1rem" }}>Clients</h3>
          {clients.length === 0 ? (
            <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>No clients found.</p>
          ) : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              {clients.map((c) => (
                <li
                  key={c.id || c.user_id}
                  onClick={() => viewProgress(c)}
                  style={{
                    padding: "0.6rem 0.75rem",
                    borderRadius: "0.5rem",
                    cursor: "pointer",
                    background: selectedClient?.id === c.id ? "#1A8FE3" : "#0D1B2A",
                    fontSize: "0.875rem",
                    color: "#e2e8f0",
                  }}
                >
                  {c.name || `${c.first_name || ""} ${c.last_name || ""}`.trim()}
                  <span style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8" }}>{c.email}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Client progress */}
        {selectedClient && (
          <div style={{ ...cardStyle, flex: 1 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, fontSize: "1rem" }}>
                {selectedClient.name || `${selectedClient.first_name || ""} ${selectedClient.last_name || ""}`.trim()} — Progress
              </h3>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  onClick={() => handleDownload("csv")}
                  disabled={!!downloading}
                  style={{ ...btnStyle, fontSize: "0.8rem", padding: "0.4rem 0.9rem" }}
                >
                  {downloading === "csv" ? "…" : "Export CSV"}
                </button>
                <button
                  onClick={() => handleDownload("pdf")}
                  disabled={!!downloading}
                  style={{ ...btnStyle, fontSize: "0.8rem", padding: "0.4rem 0.9rem", background: "#1DBF73" }}
                >
                  {downloading === "pdf" ? "…" : "Export PDF"}
                </button>
              </div>
            </div>
            {!clientProgress ? (
              <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>Loading…</p>
            ) : (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem", marginBottom: "1rem" }}>
                  <MiniCard label="Workout Frequency" value={clientProgress.workout_frequency != null ? `${clientProgress.workout_frequency}/wk` : "—"} />
                  <MiniCard label="Weight Change" value={clientProgress.weight_change_kg != null ? `${clientProgress.weight_change_kg > 0 ? "+" : ""}${clientProgress.weight_change_kg} kg` : "—"} />
                  <MiniCard label="Goal Completion" value={clientProgress.goal_completion_rate != null ? `${Math.round(clientProgress.goal_completion_rate * 100)}%` : "—"} />
                </div>
                {clientProgress.summary && (
                  <p style={{ color: "#94a3b8", fontSize: "0.875rem", margin: "0.5rem 0", lineHeight: 1.5 }}>
                    {clientProgress.summary}
                  </p>
                )}
                <p style={{ color: "#64748b", fontSize: "0.75rem", margin: "0.75rem 0 0" }}>
                  Period: {clientProgress.period?.start} → {clientProgress.period?.end}
                </p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function MiniCard({ label, value }) {
  return (
    <div style={{ background: "#0D1B2A", borderRadius: "0.5rem", padding: "0.75rem" }}>
      <p style={{ margin: "0 0 0.2rem", color: "#94a3b8", fontSize: "0.7rem", textTransform: "uppercase" }}>{label}</p>
      <p style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700, color: "#1A8FE3" }}>{value}</p>
    </div>
  );
}

const cardStyle = { background: "#112240", border: "1px solid #1e3050", borderRadius: "0.75rem", padding: "1.25rem" };
const inputStyle = { background: "#0D1B2A", border: "1px solid #1e3050", borderRadius: "0.5rem", color: "#fff", padding: "0.5rem 0.75rem", fontSize: "0.875rem", width: "100%", boxSizing: "border-box" };
const btnStyle = { background: "#1A8FE3", color: "#fff", borderRadius: "0.5rem", padding: "0.6rem 1.25rem", fontSize: "0.875rem", fontWeight: 600, cursor: "pointer", border: "none" };
const th = { textAlign: "left", padding: "0.4rem 0.6rem", fontWeight: 600 };
const td = { padding: "0.4rem 0.6rem", color: "#e2e8f0" };
