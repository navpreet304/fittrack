import React, { useEffect, useState } from "react";
import { useAuth } from "../AuthContext";
import { getMeasurements, addMeasurement } from "../api";
import Toast from "../components/Toast";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const MEASUREMENT_TYPES = [
  { value: "weight_kg",    label: "Weight",     unit: "kg"  },
  { value: "body_fat_pct", label: "Body Fat",   unit: "%"   },
  { value: "waist_cm",     label: "Waist",      unit: "cm"  },
  { value: "chest_cm",     label: "Chest",      unit: "cm"  },
  { value: "hips_cm",      label: "Hips",       unit: "cm"  },
  { value: "bicep_cm",     label: "Bicep",      unit: "cm"  },
];

export default function MeasurementsPage() {
  const { auth, baseUrl } = useAuth();
  const [measurements, setMeasurements] = useState([]);
  const [form, setForm] = useState({ measurement_type: "weight_kg", value: "", unit: "kg", recorded_date: new Date().toISOString().slice(0, 10) });
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      const data = await getMeasurements(baseUrl, auth.token);
      setMeasurements(Array.isArray(data) ? data : []);
    } catch (err) {
      setToast(err.message);
    }
  }

  useEffect(() => { load(); }, []);

  function set(field) {
    return (e) => {
      const val = e.target.value;
      if (field === "measurement_type") {
        const found = MEASUREMENT_TYPES.find((t) => t.value === val);
        setForm((f) => ({ ...f, measurement_type: val, unit: found ? found.unit : f.unit }));
      } else {
        setForm((f) => ({ ...f, [field]: val }));
      }
    };
  }

  async function handleSave(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await addMeasurement(baseUrl, auth.token, {
        measurement_type: form.measurement_type,
        value: parseFloat(form.value),
        unit: form.unit,
        recorded_date: form.recorded_date,
      });
      setForm((f) => ({ ...f, value: "" }));
      await load();
    } catch (err) {
      setToast(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Build chart data for the currently selected type (newest last)
  const chartData = measurements
    .filter((m) => m.measurement_type === form.measurement_type)
    .slice()
    .sort((a, b) => a.recorded_date.localeCompare(b.recorded_date))
    .map((m) => ({ date: m.recorded_date, value: m.value }));

  return (
    <div style={{ padding: "1.5rem", color: "#fff" }}>
      <Toast message={toast} onClose={() => setToast("")} />
      <h2 style={{ margin: "0 0 1.5rem", fontSize: "1.4rem", fontWeight: 700 }}>Measurements</h2>

      {/* Add form */}
      <div style={{ ...cardStyle, marginBottom: "1.5rem" }}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Add Measurement</h3>
        <form onSubmit={handleSave} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          <div>
            <label style={labelStyle}>Type</label>
            <select value={form.measurement_type} onChange={set("measurement_type")} style={inputStyle}>
              {MEASUREMENT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Value</label>
            <input type="number" step="any" value={form.value} onChange={set("value")} required style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Unit</label>
            <input
              value={form.unit}
              readOnly
              style={{ ...inputStyle, background: "#0a1628", color: "#64748b", cursor: "default" }}
            />
          </div>
          <div>
            <label style={labelStyle}>Date</label>
            <input type="date" value={form.recorded_date} onChange={set("recorded_date")} required style={inputStyle} />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <button type="submit" disabled={loading} style={btnStyle}>{loading ? "Saving…" : "Add Measurement"}</button>
          </div>
        </form>
      </div>

      {/* Trend chart for selected type */}
      {chartData.length > 1 && (
        <div style={{ ...cardStyle, marginBottom: "1.5rem" }}>
          <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>
            {MEASUREMENT_TYPES.find((t) => t.value === form.measurement_type)?.label} Trend
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e3050" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#112240", border: "none", color: "#fff" }} />
              <Line type="monotone" dataKey="value" stroke="#1A8FE3" strokeWidth={2} dot={{ fill: "#1A8FE3" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* History table */}
      <div style={cardStyle}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>All Measurements</h3>
        {measurements.length === 0 ? (
          <p style={{ color: "#64748b", margin: 0 }}>No measurements recorded yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1e3050", color: "#94a3b8", textAlign: "left" }}>
                <th style={thStyle}>Date</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Value</th>
                <th style={thStyle}>Unit</th>
              </tr>
            </thead>
            <tbody>
              {measurements.map((m) => {
                const label = MEASUREMENT_TYPES.find((t) => t.value === m.measurement_type)?.label ?? m.measurement_type;
                return (
                  <tr key={m.id} style={{ borderBottom: "1px solid #1e3050" }}>
                    <td style={tdStyle}>{m.recorded_date}</td>
                    <td style={tdStyle}>{label}</td>
                    <td style={{ ...tdStyle, fontWeight: 600, color: "#1A8FE3" }}>{m.value}</td>
                    <td style={tdStyle}>{m.unit}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const cardStyle = { background: "#112240", border: "1px solid #1e3050", borderRadius: "0.75rem", padding: "1.25rem" };
const inputStyle = { background: "#0D1B2A", border: "1px solid #1e3050", borderRadius: "0.5rem", color: "#fff", padding: "0.5rem 0.75rem", fontSize: "0.875rem", width: "100%", boxSizing: "border-box" };
const labelStyle = { display: "block", color: "#94a3b8", fontSize: "0.8rem", marginBottom: "0.3rem" };
const btnStyle = { background: "#1A8FE3", color: "#fff", borderRadius: "0.5rem", padding: "0.6rem 1.25rem", fontSize: "0.875rem", fontWeight: 600, cursor: "pointer", border: "none" };
const thStyle = { padding: "0.5rem 0.75rem", fontWeight: 500 };
const tdStyle = { padding: "0.5rem 0.75rem", color: "#cbd5e1" };
