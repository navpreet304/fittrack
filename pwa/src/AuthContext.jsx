import React, { createContext, useContext, useState, useCallback } from "react";

const AuthContext = createContext(null);

const STORAGE_KEY = "fittrack-pwa-auth";
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

function loadAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(loadAuth);

  const login = useCallback((authData) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(authData));
    setAuth(authData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
  }, []);

  return (
    <AuthContext.Provider value={{ auth, login, logout, baseUrl: BASE_URL }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
