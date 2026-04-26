"use client";

import type { IssueSeverity, ReviewIssue } from "@/lib/types";

type Props = {
  issue: ReviewIssue;
  selected: boolean;
  applied: boolean;
  onSelect: () => void;
  onApply: () => void;
  onDismiss: () => void;
  index: number;
};

const SEV_COLOR: Record<IssueSeverity, string> = {
  critical: "var(--error)",
  moderate: "var(--warn)",
  minor: "var(--success)",
};

const SEV_BG: Record<IssueSeverity, string> = {
  critical: "var(--error-bg)",
  moderate: "var(--warn-bg)",
  minor: "var(--success-bg)",
};

const SEV_TAG: Record<IssueSeverity, string> = {
  critical: "CRITICAL",
  moderate: "MODERATE",
  minor: "MINOR",
};

export default function IssueCard({
  issue,
  selected,
  applied,
  onSelect,
  onApply,
  onDismiss,
  index,
}: Props) {
  const color = SEV_COLOR[issue.severity];
  const bg = SEV_BG[issue.severity];
  const isInfo = issue.severity === "minor";
  return (
    <div
      onClick={onSelect}
      className="card"
      style={{
        padding: 14,
        cursor: "pointer",
        borderColor: selected ? color : "var(--border)",
        opacity: applied ? 0.6 : 1,
      }}
    >
      <div className="row between" style={{ marginBottom: 10 }}>
        <div className="row" style={{ gap: 8, minWidth: 0 }}>
          <span
            className="pill"
            style={{ background: bg, color, borderColor: "transparent" }}
          >
            {issue.title || SEV_TAG[issue.severity]}
          </span>
          <span
            className="font-mono muted"
            style={{
              fontSize: 11,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {issue.location_label}
          </span>
        </div>
        <span className="font-mono muted" style={{ fontSize: 11, flexShrink: 0 }}>
          {applied ? "✓ applied" : `#${String(index + 1).padStart(2, "0")}`}
        </span>
      </div>

      {!isInfo && issue.original_text && (
        <div
          className="font-mono"
          style={{
            fontSize: 12,
            color: "var(--error)",
            textDecoration: "line-through",
            marginBottom: 6,
            opacity: 0.85,
          }}
        >
          {issue.original_text}
        </div>
      )}
      {issue.suggested_text && (
        <div style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.5, marginBottom: 6 }}>
          {issue.suggested_text}
        </div>
      )}
      {issue.description && (
        <div style={{ fontSize: 12, color: "var(--fg-4)", fontStyle: "italic", lineHeight: 1.5 }}>
          {issue.description}
        </div>
      )}

      {selected && !isInfo && !applied && (
        <div
          className="row"
          style={{
            gap: 6,
            marginTop: 12,
            paddingTop: 12,
            borderTop: "1px solid var(--border)",
          }}
        >
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              onApply();
            }}
          >
            Apply fix
          </button>
          <button
            type="button"
            className="btn btn-soft btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              onDismiss();
            }}
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
