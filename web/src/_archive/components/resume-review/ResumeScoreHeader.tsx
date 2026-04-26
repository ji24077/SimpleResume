"use client";

import type { CategoryScores, CredibilityInfo, IssueSeverity, ReviewIssue } from "@/lib/types";
import CredibilityBadge from "./CredibilityBadge";

function ScoreCard({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = Math.round((value / max) * 100);
  let color = "text-emerald-400";
  if (pct < 60) color = "text-red-400";
  else if (pct < 75) color = "text-amber-400";

  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2 min-w-[80px]">
      <span className={`text-xl font-bold tabular-nums ${color}`}>{value}</span>
      <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">{label}</span>
    </div>
  );
}

function SeverityCount({ severity, count }: { severity: IssueSeverity; count: number }) {
  const styles: Record<IssueSeverity, string> = {
    critical: "bg-red-950/60 text-red-400 border-red-900/50",
    moderate: "bg-amber-950/60 text-amber-400 border-amber-900/50",
    minor: "bg-sky-950/60 text-sky-400 border-sky-900/50",
  };
  const labels: Record<IssueSeverity, string> = {
    critical: "Critical",
    moderate: "Moderate",
    minor: "Minor",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium ${styles[severity]}`}>
      <span className="tabular-nums">{count}</span>
      <span>{labels[severity]}</span>
    </span>
  );
}

interface ResumeScoreHeaderProps {
  overallScore: number;
  categoryScores: CategoryScores;
  credibility: CredibilityInfo;
  issues: ReviewIssue[];
  onFixTopIssues: () => void;
}

export default function ResumeScoreHeader({
  overallScore,
  categoryScores,
  credibility,
  issues,
  onFixTopIssues,
}: ResumeScoreHeaderProps) {
  const severityCounts = {
    critical: issues.filter((i) => i.severity === "critical").length,
    moderate: issues.filter((i) => i.severity === "moderate").length,
    minor: issues.filter((i) => i.severity === "minor").length,
  };

  let overallColor = "text-emerald-400";
  if (overallScore < 60) overallColor = "text-red-400";
  else if (overallScore < 75) overallColor = "text-amber-400";

  return (
    <div className="sticky top-0 z-30 border-b border-zinc-800 bg-zinc-950/95 backdrop-blur-sm">
      <div className="mx-auto max-w-[1600px] px-4 py-3">
        <div className="flex flex-wrap items-center gap-4 lg:gap-6">
          {/* Overall score */}
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-center">
              <span className={`text-3xl font-bold tabular-nums ${overallColor}`}>{overallScore}</span>
              <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Overall</span>
            </div>
          </div>

          <div className="hidden h-8 w-px bg-zinc-800 sm:block" />

          {/* Category scores */}
          <div className="flex flex-wrap gap-2">
            <ScoreCard label="ATS" value={categoryScores.ats} />
            <ScoreCard label="Impact" value={categoryScores.impact} />
            <ScoreCard label="Clarity" value={categoryScores.clarity} />
            <ScoreCard label="Format" value={categoryScores.formatting} />
          </div>

          <div className="hidden h-8 w-px bg-zinc-800 md:block" />

          {/* Credibility */}
          <CredibilityBadge credibility={credibility} />

          <div className="hidden h-8 w-px bg-zinc-800 md:block" />

          {/* Issue counts */}
          <div className="flex flex-wrap items-center gap-2">
            {severityCounts.critical > 0 && <SeverityCount severity="critical" count={severityCounts.critical} />}
            {severityCounts.moderate > 0 && <SeverityCount severity="moderate" count={severityCounts.moderate} />}
            {severityCounts.minor > 0 && <SeverityCount severity="minor" count={severityCounts.minor} />}
            {issues.length === 0 && (
              <span className="text-xs text-emerald-400">No issues found</span>
            )}
          </div>

          {/* CTA */}
          <div className="ml-auto">
            <button
              type="button"
              onClick={onFixTopIssues}
              disabled={issues.length === 0}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Fix Top Issues
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
