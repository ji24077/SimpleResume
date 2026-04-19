"use client";

import { useState, useMemo } from "react";
import type { ReviewIssue, IssueSeverity, IssueCategory } from "@/lib/types";

const SEV_DOT: Record<IssueSeverity, string> = {
  critical: "bg-red-500",
  moderate: "bg-amber-500",
  minor: "bg-sky-400",
};

const SEV_TAG: Record<IssueSeverity, { bg: string; text: string }> = {
  critical: { bg: "bg-red-500/15 border-red-500/30", text: "text-red-400" },
  moderate: { bg: "bg-amber-500/15 border-amber-500/30", text: "text-amber-400" },
  minor: { bg: "bg-sky-500/10 border-sky-500/20", text: "text-sky-400" },
};

const CAT_LABEL: Record<IssueCategory, string> = {
  ats: "ATS",
  impact: "Impact",
  clarity: "Clarity",
  formatting: "Format",
  credibility: "Credibility",
};

type Tab = "all" | "highlights" | "pins";

interface CommentPanelProps {
  issues: ReviewIssue[];
  selectedIssueId: string | null;
  onSelectIssue: (issue: ReviewIssue) => void;
  onDismiss: (issue: ReviewIssue) => void;
}

export default function CommentPanel({
  issues,
  selectedIssueId,
  onSelectIssue,
  onDismiss,
}: CommentPanelProps) {
  const [tab, setTab] = useState<Tab>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredIssues = useMemo(() => {
    let list = issues;
    if (tab === "highlights") {
      list = list.filter((i) => i.severity === "critical" || i.severity === "moderate");
    } else if (tab === "pins") {
      list = list.filter((i) => i.severity === "critical");
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (i) =>
          i.title.toLowerCase().includes(q) ||
          i.description.toLowerCase().includes(q) ||
          i.original_text.toLowerCase().includes(q)
      );
    }
    return list;
  }, [issues, tab, searchQuery]);

  const counts = useMemo(
    () => ({
      all: issues.length,
      highlights: issues.filter((i) => i.severity !== "minor").length,
      pins: issues.filter((i) => i.severity === "critical").length,
    }),
    [issues]
  );

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-zinc-800 bg-zinc-950 px-4 py-3">
        <h3 className="text-sm font-semibold text-zinc-200">Comments</h3>

        {/* Tabs like the screenshot */}
        <div className="mt-2 flex items-center gap-1">
          {(["all", "highlights", "pins"] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
                tab === t
                  ? "bg-zinc-800 text-white"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
              }`}
            >
              {t === "all" ? "All" : t === "highlights" ? "Highlights" : "Pins"}
              <span className="ml-1 text-[10px] text-zinc-600">{counts[t]}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Search */}
      <div className="shrink-0 border-b border-zinc-800 px-4 py-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search issues…"
          className="w-full rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-1.5 text-xs text-zinc-300 placeholder-zinc-600 focus:border-sky-700 focus:outline-none"
        />
      </div>

      {/* Issue list */}
      <div className="flex-1 overflow-y-auto">
        {filteredIssues.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="text-2xl text-zinc-700">✓</div>
            <p className="mt-2 text-xs text-zinc-500">
              {searchQuery ? "No matching issues." : "No issues to show."}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/50">
            {filteredIssues.map((issue) => {
              const sev = issue.severity as IssueSeverity;
              const isSelected = issue.id === selectedIssueId;

              return (
                <div
                  key={issue.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectIssue(issue)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSelectIssue(issue); }}
                  className={`group w-full cursor-pointer px-4 py-3 text-left transition hover:bg-zinc-900/50 ${
                    isSelected ? "bg-zinc-900/80 border-l-2 border-l-sky-500" : "border-l-2 border-l-transparent"
                  }`}
                >
                  {/* Location indicator */}
                  <div className="flex items-start gap-2">
                    <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${SEV_DOT[sev]}`} />
                    <div className="min-w-0 flex-1">
                      {/* Page indicator like screenshot */}
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-semibold text-zinc-500">
                          Page {issue.location.page}
                        </span>
                        <span className={`rounded-md border px-1.5 py-0.5 text-[9px] font-medium ${SEV_TAG[sev].bg} ${SEV_TAG[sev].text}`}>
                          {sev}
                        </span>
                        <span className="text-[9px] text-zinc-600">
                          {CAT_LABEL[issue.category as IssueCategory] || issue.category}
                        </span>
                      </div>

                      {/* Original text with highlight preview */}
                      {issue.original_text && (
                        <p className="mt-1.5 rounded-md bg-amber-500/8 px-2 py-1 text-[11px] italic leading-snug text-amber-200/80 line-clamp-2">
                          &quot;{issue.original_text}&quot;
                        </p>
                      )}

                      {/* Issue title as the comment */}
                      <p className="mt-1.5 text-xs leading-snug text-zinc-300">
                        {issue.title}
                      </p>

                      {/* Suggestion preview */}
                      {issue.suggested_text && (
                        <p className="mt-1 text-[11px] leading-snug text-emerald-400/70 line-clamp-2">
                          → {issue.suggested_text}
                        </p>
                      )}

                      {/* Location label */}
                      {issue.location_label && (
                        <p className="mt-1 text-[10px] text-zinc-600">
                          {issue.location_label}
                        </p>
                      )}

                      {/* Dismiss */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDismiss(issue);
                        }}
                        className="mt-1.5 text-[10px] text-zinc-600 opacity-0 group-hover:opacity-100 hover:text-zinc-400 transition"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer summary */}
      <div className="shrink-0 border-t border-zinc-800 bg-zinc-950 px-4 py-2">
        <div className="flex items-center gap-3 text-[10px] text-zinc-600">
          <span className="flex items-center gap-1">
            <span className={`h-1.5 w-1.5 rounded-full ${SEV_DOT.critical}`} />
            {issues.filter((i) => i.severity === "critical").length} critical
          </span>
          <span className="flex items-center gap-1">
            <span className={`h-1.5 w-1.5 rounded-full ${SEV_DOT.moderate}`} />
            {issues.filter((i) => i.severity === "moderate").length} moderate
          </span>
          <span className="flex items-center gap-1">
            <span className={`h-1.5 w-1.5 rounded-full ${SEV_DOT.minor}`} />
            {issues.filter((i) => i.severity === "minor").length} minor
          </span>
        </div>
      </div>
    </div>
  );
}
