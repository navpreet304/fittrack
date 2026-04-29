import React, { useEffect, useState, useCallback } from "react";
import { useAuth } from "../AuthContext";
import { getNotifications, addNotification } from "../api";
import Toast from "../components/Toast";

const STATUS_CONFIG = {
  delivered: { label: "Delivered", bg: "#2DD4BF", color: "#0D1B2A" },
  sent:      { label: "Sent",      bg: "#1DBF73", color: "#fff" },
  failed:    { label: "Failed",    bg: "#EF4444", color: "#fff" },
  pending:   { label: "Pending",   bg: "#1A8FE3", color: "#fff" },
};

export default function NotificationsPage() {
  const { auth, baseUrl } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [form, setForm] = useState({ title: "", message: "", scheduled_time: "" });
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getNotifications(baseUrl, auth.token);
      setNotifications(Array.isArray(data) ? data.slice().reverse() : []);
    } catch (err) {
      setToast(err.message);
    }
  }, [baseUrl, auth?.token]);

  useEffect(() => {
    load();
    // Refresh whenever the ReminderPoller delivers a notification
    window.addEventListener("fittrack:notif-delivered", load);
    return () => window.removeEventListener("fittrack:notif-delivered", load);
  }, [load]);

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const message = form.title ? `${form.title}: ${form.message}`.trim().replace(/: $/, "") : form.message;
      await addNotification(baseUrl, auth.token, {
        message,
        scheduled_at: form.scheduled_time || undefined,
      });
      setForm({ title: "", message: "", scheduled_time: "" });
      await load();
    } catch (err) {
      setToast(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: "1.5rem", color: "#fff" }}>
      <Toast message={toast} onClose={() => setToast("")} />
      <h2 style={{ margin: "0 0 1.5rem", fontSize: "1.4rem", fontWeight: 700 }}>Notifications</h2>

      {/* List */}
      <div style={{ ...cardStyle, marginBottom: "1.5rem" }}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Notifications</h3>
        {notifications.length === 0 ? (
          <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>No notifications yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {notifications.map((n) => {
              const { label, bg, color } = STATUS_CONFIG[n.status] || STATUS_CONFIG.pending;
              return (
                <div key={n.id} style={{ background: "#0D1B2A", borderRadius: "0.5rem", padding: "0.75rem 1rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: "0.9rem" }}>{n.message}</p>
                    {n.scheduled_at && (
                      <p style={{ margin: "0.2rem 0 0", color: "#64748b", fontSize: "0.75rem" }}>
                        Scheduled: {new Date(n.scheduled_at).toLocaleString()}
                      </p>
                    )}
                    {n.sent_at && (
                      <p style={{ margin: "0.1rem 0 0", color: "#64748b", fontSize: "0.75rem" }}>
                        Delivered: {new Date(n.sent_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      padding: "0.2rem 0.6rem",
                      borderRadius: "999px",
                      background: bg,
                      color,
                      whiteSpace: "nowrap",
                      marginLeft: "1rem",
                      flexShrink: 0,
                    }}
                  >
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Reminder Form */}
      <div style={cardStyle}>
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Add Reminder</h3>
        <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <div>
            <label style={labelStyle}>Title</label>
            <input value={form.title} onChange={set("title")} required placeholder="e.g. Take creatine" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Message</label>
            <input value={form.message} onChange={set("message")} placeholder="Optional message body" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Scheduled Time (optional)</label>
            <input type="datetime-local" value={form.scheduled_time} onChange={set("scheduled_time")} style={inputStyle} />
          </div>
          <div>
            <button type="submit" disabled={loading} style={btnStyle}>{loading ? "Saving…" : "Add Reminder"}</button>
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
