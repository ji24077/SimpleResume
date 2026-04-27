"use client";

type Props = {
  score: number | null;
  grade: string | null;
  expanded: boolean;
  onToggle: () => void;
  loading?: boolean;
};

export default function ScoreChip({ score, grade, expanded, onToggle, loading }: Props) {
  // Backend returns score on a 0-10 scale; chip displays 0-100 like the design.
  const display100 = score == null ? null : Math.round(Math.max(0, Math.min(10, score)) * 10);
  const val = display100 ?? 0;
  return (
    <button
      type="button"
      onClick={onToggle}
      className="score-chip"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "10px 16px 10px 10px",
        background: "var(--surface-1)",
        border: `1px solid ${expanded ? "var(--accent)" : "var(--border)"}`,
        borderRadius: 10,
        cursor: "pointer",
        fontFamily: "inherit",
        transition: "all .15s",
      }}
    >
      <div className="score-dial" style={{ ["--val" as string]: val, ["--size" as string]: "48px" }}>
        <div className="font-display" style={{ fontSize: 16, fontWeight: 600, lineHeight: 1 }}>
          {loading || display100 == null ? "—" : display100}
        </div>
      </div>
      <div style={{ textAlign: "left" }}>
        <div
          className="font-mono"
          style={{
            fontSize: 11,
            color: "var(--fg-4)",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            marginBottom: 2,
          }}
        >
          Score{grade ? ` · ${grade}` : ""}
        </div>
        <div style={{ fontSize: 12, color: "var(--fg-2)" }}>
          {expanded ? "Hide rubric" : "Show rubric ↓"}
        </div>
      </div>
    </button>
  );
}
