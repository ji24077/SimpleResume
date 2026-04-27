export default function ProofPills() {
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 24, alignItems: "center" }}>
      <div
        className="font-mono"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          padding: "4px 12px 4px 4px",
          background: "var(--canvas-alt)",
          border: "1px solid var(--border)",
          borderRadius: 999,
          fontSize: 12,
          color: "var(--fg-3)",
        }}
      >
        <b
          style={{
            background: "var(--accent)",
            color: "var(--accent-fg)",
            padding: "3px 8px",
            borderRadius: 999,
            fontWeight: 700,
            fontSize: 11,
          }}
        >
          +27
        </b>
        avg. score gained
      </div>
      <span
        className="pill"
        style={{ textTransform: "none", letterSpacing: 0, fontSize: 11, padding: "4px 10px" }}
      >
        100+ résumés analyzed
      </span>
      <span
        className="pill"
        style={{ textTransform: "none", letterSpacing: 0, fontSize: 11, padding: "4px 10px" }}
      >
        ~13 offers · FAANG-adj.
      </span>
      <span
        className="pill"
        style={{ textTransform: "none", letterSpacing: 0, fontSize: 11, padding: "4px 10px" }}
      >
        ATS-safe
      </span>
    </div>
  );
}
