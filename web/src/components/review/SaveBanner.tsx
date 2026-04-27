"use client";

import { useState } from "react";

export default function SaveBanner() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div
      className="card fade-in"
      style={{
        padding: "14px 18px",
        marginBottom: 18,
        display: "grid",
        gridTemplateColumns: "auto 1fr auto auto",
        gap: 16,
        alignItems: "center",
        background: "var(--accent-soft)",
        borderColor: "transparent",
        borderLeft: "3px solid var(--accent)",
        borderRadius: 8,
      }}
    >
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 8,
          background: "var(--accent)",
          color: "var(--accent-fg)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>
          Save this as your base résumé
        </div>
        <div style={{ fontSize: 12, color: "var(--fg-3)", lineHeight: 1.5 }}>
          Sign-in coming soon — keep your fixes and fork job-tuned variants per posting.
        </div>
      </div>
      <button type="button" className="btn btn-soft btn-sm" onClick={() => setDismissed(true)}>
        Not now
      </button>
      <button type="button" className="btn btn-primary btn-sm" disabled>
        Sign in to save →
      </button>
    </div>
  );
}
