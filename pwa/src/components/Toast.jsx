import React, { useEffect } from "react";
import { X } from "lucide-react";

export default function Toast({ message, onClose }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [message, onClose]);

  if (!message) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "1.5rem",
        right: "1.5rem",
        background: "#E8473F",
        color: "#fff",
        borderRadius: "0.5rem",
        padding: "0.75rem 1rem",
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        zIndex: 9999,
        maxWidth: "360px",
        boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
      }}
    >
      <span style={{ flex: 1, fontSize: "0.875rem" }}>{message}</span>
      <button
        onClick={onClose}
        style={{
          background: "transparent",
          padding: 0,
          color: "#fff",
          display: "flex",
          alignItems: "center",
        }}
      >
        <X size={16} />
      </button>
    </div>
  );
}
