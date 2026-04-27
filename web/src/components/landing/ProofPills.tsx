export default function ProofPills() {
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 24, alignItems: "center" }}>
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
        50+ offers
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
