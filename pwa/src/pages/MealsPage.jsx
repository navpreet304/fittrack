import React, { useEffect, useState, useCallback } from "react";
import { useAuth } from "../AuthContext";
import { getMeals, saveMeal, syncMeals, searchFood } from "../api";
import Toast from "../components/Toast";

const QUEUE_KEY = "fittrack-pwa-queue";

function loadQueue() {
  try { return JSON.parse(localStorage.getItem(QUEUE_KEY)) || []; } catch { return []; }
}
function saveQueue(q) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
}

export default function MealsPage() {
  const { auth, baseUrl } = useAuth();
  const [meals, setMeals] = useState([]);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [queue, setQueue] = useState(loadQueue);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [form, setForm] = useState({ meal_name: "breakfast", food_name: "", calories: "", quantity: 1 });
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  async function loadMeals(d) {
    try {
      const data = await getMeals(baseUrl, auth.token, d);
      setMeals(Array.isArray(data) ? data : []);
    } catch (err) {
      setToast(err.message);
    }
  }

  useEffect(() => { loadMeals(date); }, [date]);

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!searchQ.trim()) return;
    try {
      const results = await searchFood(baseUrl, auth.token, searchQ);
      setSearchResults(Array.isArray(results) ? results : []);
    } catch (err) {
      setToast(err.message);
    }
  }

  function selectFood(item) {
    setForm((f) => ({ ...f, food_name: item.name || item.food_name || "", calories: item.calories || "" }));
    setSearchResults([]);
    setSearchQ("");
  }

  async function handleSave(e) {
    e.preventDefault();
    const entry = {
      meal_name: form.meal_name,
      food_items: [{ name: form.food_name, calories: parseFloat(form.calories) || 0, quantity: parseFloat(form.quantity) || 1 }],
      date,
    };
    setLoading(true);
    try {
      await saveMeal(baseUrl, auth.token, entry);
      setForm({ meal_name: "breakfast", food_name: "", calories: "", quantity: 1 });
      await loadMeals(date);
    } catch {
      // offline queue
      const newQueue = [...queue, entry];
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
    try {
      await syncMeals(baseUrl, auth.token, queue);
      setQueue([]);
      saveQueue([]);
      setToast("Offline meals synced!");
      await loadMeals(date);
    } catch (err) {
      setToast(err.message);
    } finally {
      setSyncing(false);
    }
  }

  const totalCalories = meals.reduce((sum, m) => {
    const items = m.food_items || [];
    return sum + items.reduce((s, fi) => s + (fi.calories || 0), 0);
  }, 0);

  return (
    <div style={{ padding: "1.5rem", color: "#fff" }}>
      <Toast message={toast} onClose={() => setToast("")} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.4rem", fontWeight: 700 }}>Meals</h2>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={{ ...inputStyle, width: "auto" }} />
          {queue.length > 0 && (
            <button onClick={handleSync} disabled={syncing} style={{ ...btnStyle, background: "#1DBF73" }}>
              {syncing ? "Syncing…" : `Sync (${queue.length})`}
            </button>
          )}
        </div>
      </div>

      {/* Meals table */}
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.75rem" }}>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>Today's Meals</h3>
          <span style={{ color: "#1A8FE3", fontWeight: 600, fontSize: "0.9rem" }}>{totalCalories} kcal total</span>
        </div>
        {meals.length === 0 ? (
          <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>No meals logged for this date.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
            <thead>
              <tr style={{ color: "#94a3b8", borderBottom: "1px solid #1e3050" }}>
                <th style={th}>Meal</th>
                <th style={th}>Food Items</th>
                <th style={th}>Calories</th>
              </tr>
            </thead>
            <tbody>
              {meals.map((m, i) => {
                const items = m.food_items || [];
                const cals = items.reduce((s, fi) => s + (fi.calories || 0), 0);
                return (
                  <tr key={i} style={{ borderBottom: "1px solid #1e3050" }}>
                    <td style={td}>{m.meal_name}</td>
                    <td style={td}>{items.map((fi) => fi.name).join(", ") || "—"}</td>
                    <td style={td}>{cals}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Food search */}
      <div style={{ ...cardStyle, marginTop: "1.5rem" }}>
        <h3 style={{ margin: "0 0 0.75rem", fontSize: "1rem" }}>Search Food (Nutritionix)</h3>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.5rem" }}>
          <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} placeholder="e.g. banana" style={{ ...inputStyle, flex: 1 }} />
          <button type="submit" style={btnStyle}>Search</button>
        </form>
        {searchResults.length > 0 && (
          <ul style={{ listStyle: "none", margin: "0.5rem 0 0", padding: 0, display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            {searchResults.map((item, i) => (
              <li
                key={i}
                onClick={() => selectFood(item)}
                style={{ padding: "0.5rem 0.75rem", background: "#0D1B2A", borderRadius: "0.4rem", cursor: "pointer", fontSize: "0.875rem", color: "#e2e8f0" }}
              >
                {item.name || item.food_name} — {item.calories} kcal
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Add meal form */}
      <div style={{ ...cardStyle, marginTop: "1.5rem" }}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Log Meal</h3>
        <form onSubmit={handleSave} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          <div>
            <label style={labelStyle}>Meal</label>
            <select value={form.meal_name} onChange={set("meal_name")} style={inputStyle}>
              {["breakfast", "lunch", "dinner", "snack"].map((m) => <option key={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Food Name</label>
            <input value={form.food_name} onChange={set("food_name")} required style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Calories</label>
            <input type="number" min="0" value={form.calories} onChange={set("calories")} required style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Quantity</label>
            <input type="number" min="0.1" step="0.1" value={form.quantity} onChange={set("quantity")} style={inputStyle} />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <button type="submit" disabled={loading} style={btnStyle}>{loading ? "Saving…" : "Log Meal"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

const cardStyle = { background: "#112240", border: "1px solid #1e3050", borderRadius: "0.75rem", padding: "1.25rem" };
const th = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, fontSize: "0.8rem", color: "#94a3b8" };
const td = { padding: "0.5rem 0.75rem", color: "#e2e8f0", fontSize: "0.875rem" };
const inputStyle = { background: "#0D1B2A", border: "1px solid #1e3050", borderRadius: "0.5rem", color: "#fff", padding: "0.5rem 0.75rem", fontSize: "0.875rem", width: "100%", boxSizing: "border-box" };
const labelStyle = { display: "block", color: "#94a3b8", fontSize: "0.8rem", marginBottom: "0.3rem" };
const btnStyle = { background: "#1A8FE3", color: "#fff", borderRadius: "0.5rem", padding: "0.6rem 1.25rem", fontSize: "0.875rem", fontWeight: 600, cursor: "pointer", border: "none" };
