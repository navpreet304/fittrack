import React, { useEffect, useState } from "react";
import { useAuth } from "../AuthContext";
import { getGoals, saveGoal, completeGoal } from "../api";
import Toast from "../components/Toast";

export default function GoalsPage() {
  const { auth, baseUrl } = useAuth();
  const [goals, setGoals] = useState([]);
  const [form, setForm] = useState({ description: "", target_value: "", unit: "", deadline: "" });
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      const data = await getGoals(baseUrl, auth.token);
      setGoals(Array.isArray(data) ? data : []);
    } catch (err) {
      setToast(err.message);
    }
  }

  useEffect(() => { load(); }, []);

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await saveGoal(baseUrl, auth.token, auth.userId, {
        description: form.description,
        target_value: parseFloat(form.target_value),
        unit: form.unit,
        deadline: form.deadline,
      });
      setForm({ description: "", target_value: "", unit: "", deadline: "" });
      await load();
    } catch (err) {
      setToast(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleComplete(goalId) {
    try {
      await completeGoal(baseUrl, auth.token, goalId);
      await load();
    } catch (err) {
      setToast(err.message);
    }
  }

  return (
    <div style={{ padding: "1.5rem", color: "#fff" }}>
      <Toast message={toast} onClose={() => setToast("")} />
      <h2 style={{ margin: "0 0 1.5rem", fontSize: "1.4rem", fontWeight: 700 }}>Goals</h2>

      {/* Goal Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        {goals.length === 0 && (
          <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>No goals set yet.</p>
        )}
        {goals.map((g) => (
          <div key={g.id} style={{ background: "#112240", border: "1px solid #1e3050", borderRadius: "0.75rem", padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
              <p style={{ margin: 0, fontWeight: 600, fontSize: "0.95rem", flex: 1 }}>{g.description}</p>
              <span
                style={{
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  padding: "0.2rem 0.6rem",
                  borderRadius: "999px",
                  background: g.status === "achieved" ? "#1DBF73" : "#1A8FE3",
                  color: "#fff",
                  marginLeft: "0.5rem",
                  whiteSpace: "nowrap",
                }}
              >
                {g.status === "achieved" ? "Achieved" : "Active"}
              </span>
            </div>
            <p style={{ margin: "0 0 0.25rem", color: "#94a3b8", fontSize: "0.8rem" }}>
              Target: {g.target_value} {g.unit}
            </p>
            {g.deadline && (
              <p style={{ margin: "0 0 0.75rem", color: "#94a3b8", fontSize: "0.8rem" }}>Deadline: {g.deadline}</p>
            )}
            {g.status !== "achieved" && (
              <button
                onClick={() => handleComplete(g.id)}
                style={{ ...btnStyle, background: "#1DBF73", fontSize: "0.8rem", padding: "0.4rem 1rem" }}
              >
                Mark Complete
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Add Goal Form */}
      <div style={cardStyle}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Add Goal</h3>
        <form onSubmit={handleSave} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={labelStyle}>Description</label>
            <input value={form.description} onChange={set("description")} required placeholder="e.g. Run 5km under 30 min" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Target Value</label>
            <input type="number" step="any" value={form.target_value} onChange={set("target_value")} required style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Unit</label>
            <input value={form.unit} onChange={set("unit")} required placeholder="e.g. kg, km, reps" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Deadline</label>
            <input type="date" value={form.deadline} onChange={set("deadline")} required style={inputStyle} />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <button type="submit" disabled={loading} style={btnStyle}>{loading ? "Saving…" : "Add Goal"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

const cardStyle = { background: "#112240", border: "1px solid #1e3050", borderRadius: "0.75rem", padding: "1.25rem" };
const inputStyle = { background: "#0D1B2A", border: "1px solid #1e3050", borderRadius: "0.5rem", color: "#fff", padding: "0.5rem 0.75rem", fontSize: "0.875rem", width: "100%", boxSizing: "border-box" };
const labelStyle = { display: "block", color: "#94a3b8", fontSize: "0.8rem", marginBottom: "0.3rem" };
const btnStyle = { background: "#1A8FE3", color: "#fff", borderRadius: "0.5rem", padding: "0.6rem 1.25rem", fontSize: "0.875rem", fontWeight: 600, cursor: "pointer", border: "none" };
