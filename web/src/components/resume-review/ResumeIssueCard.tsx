"use client";

import type { ReviewIssue, IssueSeverity, IssueCategory } from "@/lib/types";

const SEVERITY_STYLES: Record<IssueSeverity, { dot: string; label: string }> = {
  critical: { dot: "bg-red-500", label: "Critical" },
  moderate: { dot: "bg-amber-500", label: "Moderate" },
  minor: { dot: "bg-sky-500", label: "Minor" },
};

const CATEGORY_LABELS: Record<IssueCategory, string> = {
  ats: "ATS",
  impact: "Impact",
  clarity: "Clarity",
  formatting: "Format",
  credibility: "Credibility",
};

interface ResumeIssueCardProps {
  issue: ReviewIssue;
  isSelected: boolean;
  onClick: () => void;
}

export default function ResumeIssueCard({ issue, isSelected, onClick }: ResumeIssueCardProps) {
  const sev = SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.moderate;
  const catLabel = CATEGORY_LABELS[issue.category] || issue.category;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left rounded-lg border p-3 transition focus:outline-none focus:ring-2 focus:ring-sky-500/50 ${
        isSelected
          ? "border-sky-600 bg-sky-950/30"
          : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-900/60"
      }`}
      role="option"
      aria-selected={isSelected}
      aria-label={`${sev.label} issue: ${issue.title}. Category: ${catLabel}. ${issue.location_label}`}
    >
      <div className="flex items-start gap-2">
        <span
          className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${sev.dot}`}
          aria-label={sev.label}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h4 className="truncate text-sm font-medium text-zinc-200">{issue.title}</h4>
            <span className="shrink-0 rounded-md bg-zinc-800 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400">
              {catLabel}
            </span>
          </div>
          {issue.location_label && (
            <p className="mt-0.5 truncate text-[11px] text-zinc-500">{issue.location_label}</p>
          )}
          <p className="mt-1 line-clamp-2 text-xs text-zinc-400">{issue.description}</p>
        </div>
      </div>
    </button>
  );
}
