"use client";

import type { IssueSeverity, ReviewIssue } from "@/lib/types";
import DiffBlock from "./DiffBlock";

type Props = {
  issue: ReviewIssue;
  selected: boolean;
  applied: boolean;
  dismissed?: boolean;
  pending?: boolean;
  error?: string;
  onSelect: () => void;
  onApply: () => void;
  onDismiss: () => void;
  onUndo?: () => void;
  undoLabel?: string;
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

/** Extract a short, pill-friendly tag from the backend's free-form title. */
function tagFromTitle(title: string): string {
  if (!title) return "";
  const first = title.split(/[,·•|]/)[0].trim();
  return first.toUpperCase();
}

export default function IssueCard({
  issue,
  selected,
  applied,
  dismissed,
  pending,
  error,
  onSelect,
  onApply,
  onDismiss,
  onUndo,
  undoLabel = "Undo",
  index,
}: Props) {
  const color = SEV_COLOR[issue.severity];
  const bg = SEV_BG[issue.severity];
  const hasRewrite = !!issue.suggested_text && issue.suggested_text !== issue.original_text;
  const resolved = applied || dismissed;

  return (
    <div
      onClick={onSelect}
      className="card"
      style={{
        padding: 14,
        cursor: "pointer",
        borderColor: selected ? color : "var(--border)",
        opacity: resolved ? 0.55 : 1,
      }}
    >
      <div className="row between" style={{ marginBottom: 10, gap: 8 }}>
        <div className="row" style={{ gap: 8, minWidth: 0, flex: "1 1 auto" }}>
          <span
            className="pill"
            style={{
              background: bg,
              color,
              borderColor: "transparent",
              maxWidth: 260,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              display: "inline-block",
              flexShrink: 0,
            }}
            title={issue.title || SEV_TAG[issue.severity]}
          >
            {tagFromTitle(issue.title) || SEV_TAG[issue.severity]}
          </span>
          {hasRewrite && (
            <span
              className="pill"
              style={{
                background: "var(--accent-soft)",
                color: "var(--accent)",
                borderColor: "transparent",
                flexShrink: 0,
              }}
              title="LLM-generated rewrite"
            >
              LLM rewrite
            </span>
          )}
          <span
            className="font-mono muted"
            title={issue.location_label}
            style={{
              fontSize: 11,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              minWidth: 0,
            }}
          >
            {issue.location_label}
          </span>
        </div>
        <span className="font-mono muted" style={{ fontSize: 11, flexShrink: 0 }}>
          {applied ? "✓ applied" : dismissed ? "× dismissed" : `#${String(index + 1).padStart(2, "0")}`}
        </span>
      </div>

      {hasRewrite ? (
        <DiffBlock original={issue.original_text} suggested={issue.suggested_text} />
      ) : issue.suggested_text ? (
        <div style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.5, marginBottom: 6 }}>
          {issue.suggested_text}
        </div>
      ) : null}
      {issue.description && (
        <div style={{ fontSize: 12, color: "var(--fg-4)", fontStyle: "italic", lineHeight: 1.5 }}>
          {issue.description}
        </div>
      )}

      {error && (
        <div
          style={{
            fontSize: 12,
            marginTop: 8,
            color: "var(--error)",
            background: "var(--error-bg)",
            border: "1px solid transparent",
            borderLeft: "2px solid var(--error)",
            padding: "6px 10px",
            borderRadius: 4,
          }}
        >
          {error}
        </div>
      )}

      {!resolved && (
        <div
          className="row"
          style={{
            gap: 6,
            marginTop: 12,
            paddingTop: 12,
            borderTop: "1px solid var(--border)",
          }}
        >
          {issue.suggested_text && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={pending}
              onClick={(e) => {
                e.stopPropagation();
                onApply();
              }}
            >
              {pending ? "Applying…" : "Apply fix"}
            </button>
          )}
          <button
            type="button"
            className="btn btn-soft btn-sm"
            disabled={pending}
            onClick={(e) => {
              e.stopPropagation();
              onDismiss();
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {resolved && onUndo && (
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
            className="btn btn-soft btn-sm"
            disabled={pending}
            onClick={(e) => {
              e.stopPropagation();
              onUndo();
            }}
          >
            {pending ? "Undoing…" : `↶ ${undoLabel}`}
          </button>
        </div>
      )}
    </div>
  );
}
