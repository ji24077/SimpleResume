"use client";

import { useMemo, useState } from "react";
import type { ReviewIssue, IssueCategory, IssueSeverity } from "@/lib/types";
import ResumeIssueCard from "./ResumeIssueCard";

const CATEGORY_TABS: { key: "all" | IssueCategory; label: string }[] = [
  { key: "all", label: "All" },
  { key: "ats", label: "ATS" },
  { key: "impact", label: "Impact" },
  { key: "clarity", label: "Clarity" },
  { key: "formatting", label: "Format" },
  { key: "credibility", label: "Credibility" },
];

const SEVERITY_CHIPS: { key: "all" | IssueSeverity; label: string }[] = [
  { key: "all", label: "All" },
  { key: "critical", label: "Critical" },
  { key: "moderate", label: "Moderate" },
  { key: "minor", label: "Minor" },
];

interface ResumeIssuePanelProps {
  issues: ReviewIssue[];
  selectedIssueId: string | null;
  onSelectIssue: (issue: ReviewIssue) => void;
}

export default function ResumeIssuePanel({
  issues,
  selectedIssueId,
  onSelectIssue,
}: ResumeIssuePanelProps) {
  const [categoryFilter, setCategoryFilter] = useState<"all" | IssueCategory>("all");
  const [severityFilter, setSeverityFilter] = useState<"all" | IssueSeverity>("all");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    let result = issues;
    if (categoryFilter !== "all") {
      result = result.filter((i) => i.category === categoryFilter);
    }
    if (severityFilter !== "all") {
      result = result.filter((i) => i.severity === severityFilter);
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(
        (i) =>
          i.title.toLowerCase().includes(q) ||
          i.description.toLowerCase().includes(q) ||
          i.location_label.toLowerCase().includes(q) ||
          i.original_text.toLowerCase().includes(q)
      );
    }
    return result;
  }, [issues, categoryFilter, severityFilter, search]);

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
      {/* Header */}
      <div className="shrink-0 border-b border-zinc-800 p-3">
        <h3 className="text-sm font-semibold text-zinc-200">
          Issues <span className="text-zinc-500">({issues.length})</span>
        </h3>

        {/* Search */}
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search issues…"
          className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-300 placeholder-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600/30"
          aria-label="Search issues"
        />

        {/* Category tabs */}
        <div className="mt-2 flex flex-wrap gap-1">
          {CATEGORY_TABS.map((tab) => {
            const count = tab.key === "all" ? issues.length : issues.filter((i) => i.category === tab.key).length;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setCategoryFilter(tab.key)}
                className={`rounded-md px-2 py-1 text-[11px] font-medium transition ${
                  categoryFilter === tab.key
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {tab.label}
                {count > 0 && <span className="ml-1 text-zinc-600">{count}</span>}
              </button>
            );
          })}
        </div>

        {/* Severity filter */}
        <div className="mt-1.5 flex flex-wrap gap-1">
          {SEVERITY_CHIPS.map((chip) => {
            const count = chip.key === "all" ? issues.length : issues.filter((i) => i.severity === chip.key).length;
            if (chip.key !== "all" && count === 0) return null;
            return (
              <button
                key={chip.key}
                type="button"
                onClick={() => setSeverityFilter(chip.key)}
                className={`rounded-md px-2 py-0.5 text-[10px] font-medium transition ${
                  severityFilter === chip.key
                    ? "bg-zinc-700 text-white"
                    : "text-zinc-600 hover:text-zinc-400"
                }`}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Issue list */}
      <div className="flex-1 overflow-y-auto p-2" role="listbox" aria-label="Issue list">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <div className="text-2xl text-zinc-700" aria-hidden>✓</div>
            <p className="mt-2 text-sm text-zinc-500">
              {search ? "No issues match your search." : "No issues in this category."}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((issue) => (
              <ResumeIssueCard
                key={issue.id}
                issue={issue}
                isSelected={selectedIssueId === issue.id}
                onClick={() => onSelectIssue(issue)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
