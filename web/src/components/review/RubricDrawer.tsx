"use client";

import type { ResumeScoreResponse, RubricScore } from "@/lib/types";

type Props = {
  score: ResumeScoreResponse | null;
  loading: boolean;
  onClose: () => void;
};

const RUBRIC_LABELS: Record<string, string> = {
  content_impact: "Content & impact",
  ats_compatibility: "ATS compatibility",
  structure_hierarchy: "Structure & hierarchy",
  bullet_specificity: "Bullet specificity",
  keyword_coverage: "Keyword coverage",
  repair_readiness: "Repair readiness",
  parseability: "ATS parseability",
  section_completeness: "Section completeness",
  format_consistency: "Format consistency",
};

function humanLabel(key: string): string {
  if (RUBRIC_LABELS[key]) return RUBRIC_LABELS[key];
  return key
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function RubricDrawer({ score, loading, onClose }: Props) {
  const rubricEntries: Array<[string, RubricScore]> = score
    ? Object.entries(score.resume_rubrics)
    : [];

  return (
    <div className="card fade-in" style={{ padding: 20, marginBottom: 18 }}>
      <div className="page-head" style={{ marginBottom: 14 }}>
        <div className="head-l">
          <div className="t-label">Rubric breakdown</div>
          <div style={{ fontSize: 13, color: "var(--fg-3)", marginTop: 4 }}>
            Recruiter-tested dimensions, weighted equally. Hover any row for the full criterion definition.
          </div>
        </div>
        <div className="head-r">
          {score && (
            <span className="font-mono muted" style={{ fontSize: 11 }}>
              overall {Math.round(score.overall_score * 10)} · grade {score.grade}
            </span>
          )}
          <button type="button" className="btn btn-soft btn-sm" onClick={onClose}>
            Hide
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 18 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i}>
              <div className="skeleton" style={{ height: 16, marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 6 }} />
            </div>
          ))}
        </div>
      )}

      {!loading && rubricEntries.length === 0 && (
        <p className="muted" style={{ fontSize: 13 }}>
          No rubric data available.
        </p>
      )}

      {!loading && rubricEntries.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 18 }}>
          {rubricEntries.map(([key, r]) => {
            const pct = Math.round(r.score * 10);
            const tier = pct >= 85 ? "success" : pct >= 75 ? "" : "warn";
            const color =
              pct >= 85 ? "var(--success)" : pct >= 75 ? "var(--accent)" : "var(--error)";
            return (
              <div key={key}>
                <div className="row between" style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{humanLabel(key)}</div>
                  <div className="font-mono" style={{ fontSize: 12, fontWeight: 600, color }}>
                    {pct}%
                  </div>
                </div>
                <div className={`score-bar ${tier}`}>
                  <span style={{ width: `${pct}%` }} />
                </div>
                {r.reason && (
                  <div style={{ fontSize: 12, color: "var(--fg-4)", marginTop: 6 }}>{r.reason}</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
