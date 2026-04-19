"use client";

import { useState, useCallback } from "react";
import type { ReviewIssue, IssueSeverity, IssueCategory } from "@/lib/types";

const SEVERITY_STYLES: Record<IssueSeverity, { bg: string; text: string }> = {
  critical: { bg: "bg-red-950/50", text: "text-red-400" },
  moderate: { bg: "bg-amber-950/50", text: "text-amber-400" },
  minor: { bg: "bg-sky-950/50", text: "text-sky-400" },
};

const CATEGORY_LABELS: Record<IssueCategory, string> = {
  ats: "ATS",
  impact: "Impact",
  clarity: "Clarity",
  formatting: "Format",
  credibility: "Credibility",
};

interface ResumeFixDrawerProps {
  issue: ReviewIssue | null;
  onClose: () => void;
  onApplySuggestion: (issue: ReviewIssue) => void;
  onDismiss: (issue: ReviewIssue) => void;
  onMarkNotHelpful: (issue: ReviewIssue) => void;
}

export default function ResumeFixDrawer({
  issue,
  onClose,
  onApplySuggestion,
  onDismiss,
  onMarkNotHelpful,
}: ResumeFixDrawerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    if (!issue?.suggested_text) return;
    try {
      await navigator.clipboard.writeText(issue.suggested_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard not available */
    }
  }, [issue]);

  if (!issue) return null;

  const sev = SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.moderate;
  const catLabel = CATEGORY_LABELS[issue.category] || issue.category;

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
      {/* Header */}
      <div className="flex shrink-0 items-start justify-between border-b border-zinc-800 p-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-zinc-100">{issue.title}</h3>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase ${sev.bg} ${sev.text}`}>
              {issue.severity}
            </span>
            <span className="rounded-md bg-zinc-800 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400">
              {catLabel}
            </span>
            {issue.confidence > 0 && (
              <span className="text-[10px] text-zinc-600">
                {Math.round(issue.confidence * 100)}% confidence
              </span>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-3 shrink-0 rounded-md p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
          aria-label="Close issue detail"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Location */}
        {issue.location_label && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600">Location</p>
            <p className="mt-0.5 text-xs text-zinc-400">{issue.location_label}</p>
          </div>
        )}

        {/* Why this matters — render line-by-line for bullet points */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600">Why This Matters</p>
          <div className="mt-1 space-y-1">
            {issue.description.split("\n").map((line, i) => (
              <p key={i} className="text-xs leading-relaxed text-zinc-300">
                {line}
              </p>
            ))}
          </div>
        </div>

        {/* Original text */}
        {issue.original_text && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600">Original Text</p>
            <div className="mt-1 rounded-lg border border-red-900/30 bg-red-950/20 p-3">
              <p className="text-xs leading-relaxed text-red-200/80 font-mono">{issue.original_text}</p>
            </div>
          </div>
        )}

        {/* Suggested rewrite */}
        {issue.suggested_text && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600">Suggested Rewrite</p>
            <div className="mt-1 rounded-lg border border-emerald-900/30 bg-emerald-950/20 p-3">
              <p className="text-xs leading-relaxed text-emerald-200/80 font-mono">{issue.suggested_text}</p>
            </div>
          </div>
        )}

        {/* No suggestion fallback */}
        {!issue.suggested_text && issue.original_text && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
            <p className="text-[10px] font-medium text-zinc-500">No automatic rewrite available. Use the feedback above to improve this bullet manually.</p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="shrink-0 border-t border-zinc-800 p-3">
        <div className="flex flex-wrap gap-2">
          {issue.suggested_text && (
            <>
              <button
                type="button"
                onClick={() => onApplySuggestion(issue)}
                className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-500 transition"
              >
                Apply Suggestion
              </button>
              <button
                type="button"
                onClick={handleCopy}
                className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-800 transition"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => onDismiss(issue)}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-zinc-800 transition"
          >
            Dismiss
          </button>
          <button
            type="button"
            onClick={() => onMarkNotHelpful(issue)}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-400 transition"
          >
            Not Helpful
          </button>
        </div>
      </div>
    </div>
  );
}
