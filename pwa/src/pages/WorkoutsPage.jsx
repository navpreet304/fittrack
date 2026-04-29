import React, { useEffect, useState } from "react";
import { useAuth } from "../AuthContext";
import { getWorkouts, saveWorkout } from "../api";
import Toast from "../components/Toast";

const EXERCISE_TYPES = ["Running", "Cycling", "Swimming", "Push-ups", "Squats", "Plank", "Deadlift", "Pull-ups", "Yoga", "HIIT", "Walking", "Other"];

const WORKOUT_QUEUE_KEY = "fittrack-workout-queue";
function loadQueue() {
  try { return JSON.parse(localStorage.getItem(WORKOUT_QUEUE_KEY)) || []; } catch { return []; }
}
function saveQueue(q) { localStorage.setItem(WORKOUT_QUEUE_KEY, JSON.stringify(q)); }

const emptyForm = () => ({ exercise_name: "Running", duration_minutes: "", sets: "", reps: "", notes: "", session_date: new Date().toISOString().slice(0, 10) });

export default function WorkoutsPage() {
  const { auth, baseUrl } = useAuth();
  const [workouts, setWorkouts] = useState([]);
  const [form, setForm] = useState(emptyForm());
  const [queue, setQueue] = useState(loadQueue);
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  async function load() {
    try {
      const data = await getWorkouts(baseUrl, auth.token);
      setWorkouts(Array.isArray(data) ? data.slice().reverse() : []);
    } catch (err) {
      setToast(err.message);
    }
  }

  useEffect(() => { load(); }, []);

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  function buildPayload(f) {
    return {
      session_date: f.session_date,
      exercises: [{
        name: f.exercise_name,
        duration_minutes: parseInt(f.duration_minutes, 10) || 0,
        sets: parseInt(f.sets, 10) || 0,
        reps: parseInt(f.reps, 10) || 0,
        notes: f.notes,
      }],
    };
  }

  async function handleSave(e) {
    e.preventDefault();
    setLoading(true);
    const payload = buildPayload(form);
    try {
      await saveWorkout(baseUrl, auth.token, payload);
      setForm(emptyForm());
      await load();
    } catch {
      const newQueue = [...queue, payload];
      setQueue(newQueue);
      saveQueue(newQueue);
      setToast("Saved offline — will sync when reconnected.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSync() {
    if (queue.length === 0) return;
    setSyncing(true);
    const failed = [];
    for (const entry of queue) {
      try {
        await saveWorkout(baseUrl, auth.token, entry);
      } catch {
        failed.push(entry);
      }
    }
    setQueue(failed);
    saveQueue(failed);
    if (failed.length === 0) {
      setToast("All offline workouts synced!");
      await load();
    } else {
      setToast(`${queue.length - failed.length} synced, ${failed.length} still offline.`);
    }
    setSyncing(false);
  }

  return (
    <div style={{ padding: "1.5rem", color: "#fff" }}>
      <Toast message={toast} onClose={() => setToast("")} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.4rem", fontWeight: 700 }}>Workouts</h2>
        {queue.length > 0 && (
          <button onClick={handleSync} disabled={syncing} style={{ ...btnStyle, background: "#1DBF73" }}>
            {syncing ? "Syncing…" : `Sync (${queue.length})`}
          </button>
        )}
      </div>

      {/* Table */}
      <div style={cardStyle}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Workout History</h3>
        {workouts.length === 0 ? (
          <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>No workouts yet.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ color: "#94a3b8", borderBottom: "1px solid #1e3050" }}>
                  <th style={th}>Date</th>
                  <th style={th}>Exercise(s)</th>
                  <th style={th}>Duration (min)</th>
                  <th style={th}>Sets × Reps</th>
                  <th style={th}>Notes</th>
                </tr>
              </thead>
              <tbody>
                {workouts.map((w, i) => {
                  const ex = w.exercises || [];
                  const names = ex.map((e) => e.name).join(", ") || "—";
                  const setsReps = ex.length > 0 && (ex[0].sets || ex[0].reps)
                    ? `${ex[0].sets}×${ex[0].reps}`
                    : "—";
                  const notes = ex.length > 0 ? ex[0].notes || "—" : "—";
                  return (
                    <tr key={i} style={{ borderBottom: "1px solid #1e3050" }}>
                      <td style={td}>{w.session_date || "—"}</td>
                      <td style={td}>{names}</td>
                      <td style={td}>{w.total_duration_minutes ?? "—"}</td>
                      <td style={td}>{setsReps}</td>
                      <td style={td}>{notes}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Workout Form */}
      <div style={{ ...cardStyle, marginTop: "1.5rem" }}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Add Workout</h3>
        <form onSubmit={handleSave} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          <div>
            <label style={labelStyle}>Date</label>
            <input type="date" value={form.session_date} onChange={set("session_date")} required style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Exercise</label>
            <select value={form.exercise_name} onChange={set("exercise_name")} style={inputStyle}>
              {EXERCISE_TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Duration (minutes)</label>
            <input type="number" min="1" value={form.duration_minutes} onChange={set("duration_minutes")} required style={inputStyle} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <div>
              <label style={labelStyle}>Sets</label>
              <input type="number" min="0" value={form.sets} onChange={set("sets")} placeholder="0" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Reps</label>
              <input type="number" min="0" value={form.reps} onChange={set("reps")} placeholder="0" style={inputStyle} />
            </div>
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={labelStyle}>Notes</label>
            <input value={form.notes} onChange={set("notes")} placeholder="Optional notes" style={inputStyle} />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <button type="submit" disabled={loading} style={btnStyle}>
              {loading ? "Saving…" : "Save Workout"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const cardStyle = { background: "#112240", border: "1px solid #1e3050", borderRadius: "0.75rem", padding: "1.25rem" };
const th = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, fontSize: "0.8rem" };
const td = { padding: "0.5rem 0.75rem", color: "#e2e8f0" };
const inputStyle = { background: "#0D1B2A", border: "1px solid #1e3050", borderRadius: "0.5rem", color: "#fff", padding: "0.5rem 0.75rem", fontSize: "0.875rem", width: "100%", boxSizing: "border-box" };
const labelStyle = { display: "block", color: "#94a3b8", fontSize: "0.8rem", marginBottom: "0.3rem" };
const btnStyle = { background: "#1A8FE3", color: "#fff", borderRadius: "0.5rem", padding: "0.6rem 1.5rem", fontSize: "0.9rem", fontWeight: 600, cursor: "pointer", border: "none" };
