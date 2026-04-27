"use client";

import { diffWords } from "@/lib/diff";

type Props = {
  original: string;
  suggested: string;
};

export default function DiffBlock({ original, suggested }: Props) {
  if (!original) {
    return (
      <div style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.5, marginBottom: 6 }}>
        {suggested}
      </div>
    );
  }
  if (!suggested) {
    return (
      <div
        className="font-mono"
        style={{
          fontSize: 12,
          color: "var(--fg-4)",
          textDecoration: "line-through",
          marginBottom: 6,
          opacity: 0.85,
        }}
      >
        {original}
      </div>
    );
  }

  const segments = diffWords(original, suggested);

  const removedSegs = segments.filter((s) => s.kind !== "add");
  const addedSegs = segments.filter((s) => s.kind !== "del");

  return (
    <div
      style={{
        marginBottom: 6,
        background: "var(--canvas-alt)",
        border: "1px solid var(--border)",
        borderRadius: 6,
        padding: "10px 12px",
        fontSize: 13,
        lineHeight: 1.55,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
        <span
          aria-hidden
          style={{
            fontFamily: "var(--font-mono-jb), monospace",
            fontWeight: 700,
            color: "var(--error)",
            flexShrink: 0,
            opacity: 0.9,
          }}
        >
          −
        </span>
        <div style={{ flex: 1, minWidth: 0, color: "var(--fg-3)" }}>
          {removedSegs.map((seg, i) =>
            seg.kind === "del" ? (
              <span
                key={i}
                style={{
                  background: "var(--error-bg)",
                  color: "var(--error)",
                  textDecoration: "line-through",
                  borderRadius: 2,
                  padding: "0 1px",
                }}
              >
                {seg.text}
              </span>
            ) : (
              <span key={i}>{seg.text}</span>
            ),
          )}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginTop: 4 }}>
        <span
          aria-hidden
          style={{
            fontFamily: "var(--font-mono-jb), monospace",
            fontWeight: 700,
            color: "var(--success)",
            flexShrink: 0,
            opacity: 0.9,
          }}
        >
          +
        </span>
        <div style={{ flex: 1, minWidth: 0, color: "var(--fg-1)" }}>
          {addedSegs.map((seg, i) =>
            seg.kind === "add" ? (
              <span
                key={i}
                style={{
                  background: "var(--success-bg)",
                  color: "var(--success)",
                  borderRadius: 2,
                  padding: "0 1px",
                  fontWeight: 500,
                }}
              >
                {seg.text}
              </span>
            ) : (
              <span key={i}>{seg.text}</span>
            ),
          )}
        </div>
      </div>
    </div>
  );
}
