const STEPS = [
  { n: "01", t: "Score", d: "12 rubric checks: ATS parse, metrics density, action-verb strength, hierarchy." },
  { n: "02", t: "Rewrite", d: "Weak bullets get rewritten with concrete numbers, scope, outcomes — never invented." },
  { n: "03", t: "Compile", d: "Ships a clean LaTeX source plus a one-page PDF. Diff against your draft." },
];

export default function StepsBand() {
  return (
    <div
      style={{
        marginTop: 64,
        paddingTop: 32,
        borderTop: "1px solid var(--border)",
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 32,
      }}
    >
      {STEPS.map((s) => (
        <div key={s.n}>
          <div
            className="font-mono"
            style={{ fontSize: 11, color: "var(--accent)", letterSpacing: "0.1em", marginBottom: 8 }}
          >
            {s.n}
          </div>
          <div className="font-display" style={{ fontSize: 20, fontWeight: 600, marginBottom: 6 }}>
            {s.t}
          </div>
          <div style={{ fontSize: 13, color: "var(--fg-3)", lineHeight: 1.6 }}>{s.d}</div>
        </div>
      ))}
    </div>
  );
}
