import DropZone from "./DropZone";
import MockResume from "./MockResume";
import ProofPills from "./ProofPills";

export default function Hero() {
  return (
    <div style={{ position: "relative" }}>
      <div className="hero-grid" aria-hidden />
      <div
        style={{
          position: "relative",
          display: "grid",
          gridTemplateColumns: "1.1fr 1fr",
          gap: 48,
          alignItems: "start",
          paddingTop: 24,
        }}
      >
        <div>
          <div
            className="t-eyebrow"
            style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}
          >
            <span style={{ width: 6, height: 6, background: "var(--accent)", borderRadius: "50%" }} />
            Upload your résumé. Get it optimized.
          </div>
          <h1
            className="font-display"
            style={{ fontSize: 64, lineHeight: 1.02, margin: "0 0 20px", fontWeight: 600 }}
          >
            Your résumé,
            <br />
            <em style={{ color: "var(--accent)", fontStyle: "italic", fontWeight: 500 }}>simplified</em>.
          </h1>
          <p
            style={{
              fontSize: 15,
              lineHeight: 1.6,
              color: "var(--fg-3)",
              maxWidth: 520,
              margin: "0 0 28px",
            }}
          >
            Upload a PDF or paste plain text. We score it against 100+ recruiter-tested patterns, rewrite
            weak bullets with metrics, and ship a clean LaTeX/PDF — review-only, never auto-sent.
          </p>

          <DropZone />

          <ProofPills />
        </div>

        <div>
          <div className="row between" style={{ marginBottom: 12 }}>
            <div className="t-label">Sample output</div>
            <div
              className="font-mono"
              style={{
                fontSize: 10,
                color: "var(--fg-5)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              review → rewrite → render
            </div>
          </div>
          <div style={{ transform: "scale(0.92)", transformOrigin: "top right" }}>
            <MockResume />
          </div>
        </div>
      </div>
    </div>
  );
}
