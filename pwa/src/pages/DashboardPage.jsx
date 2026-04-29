import React, { useEffect, useState } from "react";
import { useAuth } from "../AuthContext";
import { getWorkouts, getMeals, getGoals, getMeasurementsLatest, getProgress } from "../api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

const COLORS = ["#1A8FE3", "#1DBF73"];

export default function DashboardPage() {
  const { auth, baseUrl } = useAuth();
  const [data, setData] = useState({
    workoutCount: 0,
    caloriesToday: 0,
    latestMeasurement: null,
    goalsTotal: 0,
    goalsCompleted: 0,
    recentWorkouts: [],
    calorieData: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const todayStr = new Date().toISOString().slice(0, 10);
        const [workouts, meals, goals, measurement] = await Promise.allSettled([
          getWorkouts(baseUrl, auth.token),
          getMeals(baseUrl, auth.token, todayStr),
          getGoals(baseUrl, auth.token),
          getMeasurementsLatest(baseUrl, auth.token),
        ]);

        const ws = workouts.status === "fulfilled" ? workouts.value : [];
        const ms = meals.status === "fulfilled" ? (Array.isArray(meals.value) ? meals.value : []) : [];
        const gs = goals.status === "fulfilled" ? (Array.isArray(goals.value) ? goals.value : []) : [];
        const lm = measurement.status === "fulfilled" ? measurement.value : null;

        const caloriesToday = ms.reduce((sum, m) => {
          const items = m.food_items || [];
          return sum + items.reduce((s, fi) => s + (fi.calories || 0), 0);
        }, 0);

        const goalsCompleted = gs.filter((g) => g.status === "achieved").length;

        const recent = Array.isArray(ws) ? ws.slice(-7).reverse() : [];
        const calorieData = recent.map((w) => ({
          name: (w.session_date || "").slice(5), // show MM-DD
          Duration: w.total_duration_minutes || 0,
        }));

        setData({
          workoutCount: Array.isArray(ws) ? ws.length : 0,
          caloriesToday,
          latestMeasurement: lm,
          goalsTotal: gs.length,
          goalsCompleted,
          recentWorkouts: recent,
          calorieData,
        });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [auth, baseUrl]);

  if (loading) return <LoadingScreen />;

  const pieData = [
    { name: "Completed", value: data.goalsCompleted },
    { name: "Active", value: Math.max(0, data.goalsTotal - data.goalsCompleted) },
  ];

  return (
    <div style={{ padding: "1.5rem", color: "#fff" }}>
      <h2 style={{ margin: "0 0 1.5rem", fontSize: "1.4rem", fontWeight: 700 }}>Dashboard</h2>

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
        <StatCard label="Total Workouts" value={data.workoutCount} />
        <StatCard label="Calories Today" value={data.caloriesToday} unit="kcal" />
        <StatCard
          label="Latest Measurement"
          value={data.latestMeasurement ? `${data.latestMeasurement.value} ${data.latestMeasurement.unit}` : "—"}
        />
        <StatCard
          label="Goals Completed"
          value={`${data.goalsCompleted} / ${data.goalsTotal}`}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", flexWrap: "wrap" }}>
        {/* Calories bar chart */}
        <div style={cardStyle}>
          <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Duration per Session (last 7)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data.calorieData}>
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#112240", border: "none", color: "#fff" }} />
              <Bar dataKey="Duration" fill="#1A8FE3" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Goal completion doughnut */}
        <div style={cardStyle}>
          <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Goal Completion</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} dataKey="value" innerRadius={55} outerRadius={80} paddingAngle={3}>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Legend formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 12 }}>{v}</span>} />
              <Tooltip contentStyle={{ background: "#112240", border: "none", color: "#fff" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent workouts */}
      <div style={{ ...cardStyle, marginTop: "1.5rem" }}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Recent Workouts</h3>
        {data.recentWorkouts.length === 0 ? (
          <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>No workouts recorded yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
            <thead>
              <tr style={{ color: "#94a3b8", borderBottom: "1px solid #1e3050" }}>
                <th style={th}>Date</th>
                <th style={th}>Exercise</th>
                <th style={th}>Duration (min)</th>
                <th style={th}>Exercises</th>
              </tr>
            </thead>
            <tbody>
              {data.recentWorkouts.map((w, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e3050" }}>
                  <td style={td}>{w.session_date || "—"}</td>
                  <td style={td}>{(w.exercises || [])[0]?.name || "—"}</td>
                  <td style={td}>{w.total_duration_minutes ?? "—"}</td>
                  <td style={td}>{w.exercises?.length ?? "—"} exercise(s)</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, unit }) {
  return (
    <div style={{ background: "#112240", border: "1px solid #1e3050", borderRadius: "0.75rem", padding: "1.25rem" }}>
      <p style={{ margin: "0 0 0.25rem", color: "#94a3b8", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
      <p style={{ margin: 0, fontSize: "1.6rem", fontWeight: 700, color: "#1A8FE3" }}>
        {value}{unit ? <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "#94a3b8", marginLeft: "0.3rem" }}>{unit}</span> : null}
      </p>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#94a3b8" }}>
      Loading…
    </div>
  );
}

const cardStyle = {
  background: "#112240",
  border: "1px solid #1e3050",
  borderRadius: "0.75rem",
  padding: "1.25rem",
};

const th = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600 };
const td = { padding: "0.5rem 0.75rem", color: "#e2e8f0" };
