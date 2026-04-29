import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { login as apiLogin, register as apiRegister } from "../api";

export default function LoginPage() {
  const { login, baseUrl } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    date_of_birth: "",
    role: "user",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        const data = await apiLogin(baseUrl, form.email, form.password);
        login({ token: data.access_token, userId: data.user_id, role: data.role });
        navigate("/dashboard");
      } else {
        await apiRegister(baseUrl, {
          email: form.email,
          password: form.password,
          first_name: form.first_name,
          last_name: form.last_name,
          date_of_birth: form.date_of_birth,
          role: form.role,
        });
        setMode("login");
        setError("Registered! Please log in.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0D1B2A",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "#112240",
          border: "1px solid #1e3050",
          borderRadius: "1rem",
          padding: "2rem",
          width: "100%",
          maxWidth: "420px",
          color: "#fff",
        }}
      >
        <h1 style={{ margin: "0 0 0.25rem", fontSize: "1.5rem", fontWeight: 700 }}>
          FitTrack Pro
        </h1>
        <p style={{ margin: "0 0 1.5rem", color: "#94a3b8", fontSize: "0.875rem" }}>
          {mode === "login" ? "Sign in to your account" : "Create a new account"}
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {mode === "register" && (
            <>
              <input
                placeholder="First name"
                value={form.first_name}
                onChange={set("first_name")}
                required
                style={inputStyle}
              />
              <input
                placeholder="Last name"
                value={form.last_name}
                onChange={set("last_name")}
                required
                style={inputStyle}
              />
              <input
                type="date"
                placeholder="Date of birth"
                value={form.date_of_birth}
                onChange={set("date_of_birth")}
                required
                style={inputStyle}
              />
              <select value={form.role} onChange={set("role")} style={inputStyle}>
                <option value="user">User</option>
                <option value="coach">Coach</option>
              </select>
            </>
          )}
          <input
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={set("email")}
            required
            style={inputStyle}
          />
          <input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={set("password")}
            required
            style={inputStyle}
          />
          {error && (
            <p style={{ color: "#E8473F", fontSize: "0.8rem", margin: 0 }}>{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            style={btnStyle}
          >
            {loading ? "Please wait…" : mode === "login" ? "Login" : "Register"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: "1rem", color: "#94a3b8", fontSize: "0.875rem" }}>
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <button
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            style={{ background: "transparent", color: "#1A8FE3", padding: 0, fontSize: "0.875rem" }}
          >
            {mode === "login" ? "Register" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}

const inputStyle = {
  background: "#0D1B2A",
  border: "1px solid #1e3050",
  borderRadius: "0.5rem",
  color: "#fff",
  padding: "0.6rem 0.75rem",
  fontSize: "0.875rem",
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

const btnStyle = {
  background: "#1A8FE3",
  color: "#fff",
  borderRadius: "0.5rem",
  padding: "0.65rem",
  fontSize: "0.9rem",
  fontWeight: 600,
  cursor: "pointer",
  border: "none",
};
