"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import type { ReviewIssue, IssueSeverity } from "@/lib/types";

const SEVERITY_COLORS: Record<IssueSeverity, { bg: string; border: string; ring: string }> = {
  critical: { bg: "bg-red-500/15", border: "border-red-500/40", ring: "ring-red-500/30" },
  moderate: { bg: "bg-amber-500/15", border: "border-amber-500/40", ring: "ring-amber-500/30" },
  minor: { bg: "bg-sky-500/10", border: "border-sky-500/30", ring: "ring-sky-500/20" },
};

interface ResumeHighlightOverlayProps {
  pdfUrl: string | null;
  issues: ReviewIssue[];
  selectedIssueId: string | null;
  onSelectIssue: (issue: ReviewIssue) => void;
}

export default function ResumeHighlightOverlay({
  pdfUrl,
  issues,
  selectedIssueId,
  onSelectIssue,
}: ResumeHighlightOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const issuesWithFallbackPositions = issues.map((issue, index) => {
    if (issue.location.bbox) {
      return { ...issue, _top: issue.location.bbox.y, _height: issue.location.bbox.height };
    }
    const step = 48;
    const top = 60 + index * step;
    return { ...issue, _top: top, _height: 36 };
  });

  const scrollToIssue = useCallback((issueId: string) => {
    const el = containerRef.current?.querySelector(`[data-issue-id="${issueId}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, []);

  useEffect(() => {
    if (selectedIssueId) {
      scrollToIssue(selectedIssueId);
    }
  }, [selectedIssueId, scrollToIssue]);

  if (!pdfUrl) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/40 p-8">
        <div className="text-center">
          <div className="text-3xl text-zinc-700" aria-hidden>📄</div>
          <p className="mt-3 text-sm text-zinc-500">Upload a resume to see the preview with annotations.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full overflow-hidden rounded-xl border border-zinc-800 bg-white" ref={containerRef}>
      {/* PDF iframe */}
      <iframe
        title="Resume PDF Preview"
        src={`${pdfUrl}#toolbar=0&navpanes=0`}
        className="h-full w-full"
        style={{ minHeight: "700px" }}
      />

      {/* Overlay for issue indicators (side markers) */}
      <div className="pointer-events-none absolute inset-0">
        {issuesWithFallbackPositions.map((issue) => {
          const isSelected = selectedIssueId === issue.id;
          const isHovered = hoveredId === issue.id;
          const colors = SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.moderate;

          return (
            <div
              key={issue.id}
              data-issue-id={issue.id}
              className={`pointer-events-auto absolute right-0 cursor-pointer transition-all ${
                isSelected ? `w-6 ${colors.bg} border-l-2 ${colors.border} ring-2 ${colors.ring}` :
                isHovered ? `w-4 ${colors.bg} border-l-2 ${colors.border}` :
                `w-3 ${colors.bg} border-l ${colors.border} opacity-70`
              }`}
              style={{ top: `${issue._top}px`, height: `${issue._height}px` }}
              onClick={(e) => { e.stopPropagation(); onSelectIssue(issue); }}
              onMouseEnter={() => setHoveredId(issue.id)}
              onMouseLeave={() => setHoveredId(null)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSelectIssue(issue); }}
              aria-label={`${issue.severity} issue: ${issue.title}`}
            >
              {(isSelected || isHovered) && (
                <div className="absolute right-full top-1/2 mr-2 -translate-y-1/2 whitespace-nowrap rounded-md bg-zinc-900 px-2 py-1 text-[10px] text-zinc-300 shadow-lg border border-zinc-700">
                  {issue.title}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
