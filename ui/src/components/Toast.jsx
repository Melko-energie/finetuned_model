import { useState, useEffect } from "react";

export default function Toast({ message, type = "success", onClose }) {
  const [visible, setVisible] = useState(true);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setExiting(true);
      setTimeout(() => {
        setVisible(false);
        if (onClose) onClose();
      }, 300);
    }, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  if (!visible || !message) return null;

  const isError = type === "error";

  return (
    <div
      style={{
        position: "fixed",
        top: 20,
        right: 20,
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "12px 20px",
        borderRadius: 10,
        background: isError ? "#FEF2F2" : "#ECFDF5",
        border: `1px solid ${isError ? "#FECACA" : "#A7F3D0"}`,
        color: isError ? "#991B1B" : "#065F46",
        fontSize: 14,
        fontWeight: 600,
        fontFamily: "'Inter', sans-serif",
        boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
        animation: exiting ? "toast-out 0.3s ease forwards" : "toast-in 0.3s ease forwards",
        maxWidth: 420,
      }}
    >
      <span style={{ fontSize: 18 }}>{isError ? "\u2716" : "\u2714"}</span>
      <span>{message}</span>
      <button
        onClick={() => {
          setExiting(true);
          setTimeout(() => { setVisible(false); if (onClose) onClose(); }, 300);
        }}
        style={{
          marginLeft: 8, background: "none", border: "none", cursor: "pointer",
          fontSize: 16, color: isError ? "#991B1B" : "#065F46", opacity: 0.6,
        }}
      >
        &times;
      </button>
    </div>
  );
}
