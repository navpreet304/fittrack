import React, { useEffect, useState, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import Sidebar from "./components/Sidebar";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import WorkoutsPage from "./pages/WorkoutsPage";
import MealsPage from "./pages/MealsPage";
import GoalsPage from "./pages/GoalsPage";
import MeasurementsPage from "./pages/MeasurementsPage";
import NotificationsPage from "./pages/NotificationsPage";
import CoachDashboard from "./pages/CoachDashboard";
import { getDueNotifications, deliverNotification } from "./api";

// ── Toast notification overlay ────────────────────────────────────────────────
function ToastContainer({ toasts, onDismiss }) {
  return (
    <div style={{
      position: "fixed",
      bottom: "1.5rem",
      right: "1.5rem",
      zIndex: 9999,
      display: "flex",
      flexDirection: "column",
      gap: "0.75rem",
      maxWidth: "360px",
    }}>
      {toasts.map((t) => (
        <div key={t.id} style={{
          background: "#1E3A5F",
          border: "1px solid #2DD4BF",
          borderRadius: "10px",
          padding: "0.9rem 1.1rem",
          color: "#E0F2FE",
          boxShadow: "0 4px 18px rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "flex-start",
          gap: "0.75rem",
        }}>
          <span style={{ fontSize: "1.3rem", lineHeight: 1 }}>🔔</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, marginBottom: "0.2rem", color: "#2DD4BF" }}>
              Workout Reminder
            </div>
            <div style={{ fontSize: "0.9rem" }}>{t.message}</div>
          </div>
          <button
            onClick={() => onDismiss(t.id)}
            style={{
              background: "none",
              border: "none",
              color: "#94A3B8",
              cursor: "pointer",
              fontSize: "1.1rem",
              lineHeight: 1,
              padding: 0,
            }}
            aria-label="Dismiss"
          >✕</button>
        </div>
      ))}
    </div>
  );
}

// ── Reminder polling (runs while user is logged in) ───────────────────────────
const POLL_INTERVAL_MS = 30_000;

function ReminderPoller() {
  const { auth, baseUrl } = useAuth();
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((toastId) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId));
  }, []);

  useEffect(() => {
    if (!auth?.token) return;

    async function poll() {
      try {
        const due = await getDueNotifications(baseUrl, auth.token);
        if (!Array.isArray(due) || due.length === 0) return;
        for (const notif of due) {
          if (!notif?.id) continue;
          // Mark delivered on backend immediately
          await deliverNotification(baseUrl, auth.token, notif.id).catch(() => {});
          // Notify NotificationsPage to refresh its list
          window.dispatchEvent(new CustomEvent("fittrack:notif-delivered"));
          // Show toast
          const toastId = `${notif.id}-${Date.now()}`;
          setToasts((prev) => [...prev, { id: toastId, message: notif.message }]);
          // Auto-dismiss after 8 seconds
          setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== toastId)), 8000);
        }
      } catch {
        // silently ignore polling errors (e.g. token expired)
      }
    }

    poll(); // fire immediately on login
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [auth?.token, baseUrl]);

  return <ToastContainer toasts={toasts} onDismiss={dismiss} />;
}

function ProtectedLayout() {
  const { auth } = useAuth();
  if (!auth) return <Navigate to="/login" replace />;
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0D1B2A" }}>
      <Sidebar />
      <main style={{ flex: 1, overflowY: "auto" }}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/workouts" element={<WorkoutsPage />} />
          <Route path="/meals" element={<MealsPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/measurements" element={<MeasurementsPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/coach" element={<CoachDashboard />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
      <ReminderPoller />
    </div>
  );
}

function PublicRoute({ children }) {
  const { auth } = useAuth();
  if (auth) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
