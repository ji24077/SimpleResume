"use client";

import { useState, useCallback } from "react";
import type { ReviewResponse, ReviewIssue } from "@/lib/types";
import ResumeScoreHeader from "./ResumeScoreHeader";
import ResumeIssuePanel from "./ResumeIssuePanel";
import AnnotatedResume from "./AnnotatedResume";
import ResumeFixDrawer from "./ResumeFixDrawer";

interface ReviewWorkspaceProps {
  review: ReviewResponse;
  pdfUrl: string | null;
}

export default function ReviewWorkspace({ review, pdfUrl }: ReviewWorkspaceProps) {
  const [selectedIssue, setSelectedIssue] = useState<ReviewIssue | null>(null);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [mobileView, setMobileView] = useState<"preview" | "issues">("issues");

  const visibleIssues = review.issues.filter((i) => !dismissedIds.has(i.id));

  const handleSelectIssue = useCallback((issue: ReviewIssue) => {
    setSelectedIssue((prev) => (prev?.id === issue.id ? null : issue));
  }, []);

  const handleFixTopIssues = useCallback(() => {
    const first = visibleIssues.find((i) => i.severity === "critical") || visibleIssues[0];
    if (first) {
      setSelectedIssue(first);
    }
  }, [visibleIssues]);

  const handleApplySuggestion = useCallback((issue: ReviewIssue) => {
    // TODO: Integrate with resume editing when available
    console.log("Apply suggestion for:", issue.id, issue.suggested_text);
    setDismissedIds((prev) => new Set([...prev, issue.id]));
    setSelectedIssue(null);
  }, []);

  const handleDismiss = useCallback((issue: ReviewIssue) => {
    setDismissedIds((prev) => new Set([...prev, issue.id]));
    setSelectedIssue(null);
  }, []);

  const handleMarkNotHelpful = useCallback((issue: ReviewIssue) => {
    // TODO: Send feedback to backend
    console.log("Marked not helpful:", issue.id);
    setDismissedIds((prev) => new Set([...prev, issue.id]));
    setSelectedIssue(null);
  }, []);

  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100">
      {/* Sticky score header */}
      <ResumeScoreHeader
        overallScore={review.overall_score}
        categoryScores={review.category_scores}
        credibility={review.credibility}
        issues={visibleIssues}
        onFixTopIssues={handleFixTopIssues}
      />

      {/* Mobile view toggle */}
      <div className="flex shrink-0 border-b border-zinc-800 lg:hidden">
        <button
          type="button"
          onClick={() => setMobileView("issues")}
          className={`flex-1 py-2.5 text-center text-xs font-medium transition ${
            mobileView === "issues" ? "bg-zinc-900 text-white" : "text-zinc-500"
          }`}
        >
          Issues ({visibleIssues.length})
        </button>
        <button
          type="button"
          onClick={() => setMobileView("preview")}
          className={`flex-1 py-2.5 text-center text-xs font-medium transition ${
            mobileView === "preview" ? "bg-zinc-900 text-white" : "text-zinc-500"
          }`}
        >
          Preview
        </button>
      </div>

      {/* Main workspace: left = preview, right = issues + detail drawer */}
      <div className="flex flex-1 overflow-hidden">
        {/* Annotated resume (left) — hidden on mobile when issues tab selected */}
        <div className={`flex-1 overflow-hidden p-3 ${mobileView === "issues" ? "hidden lg:block" : ""}`}>
          <AnnotatedResume
            sections={review.sections}
            issues={visibleIssues}
            selectedIssueId={selectedIssue?.id ?? null}
            onClickIssue={handleSelectIssue}
            pdfUrl={pdfUrl}
          />
        </div>

        {/* Right panel — hidden on mobile when preview tab selected */}
        <div
          className={`flex w-full flex-col overflow-hidden border-l border-zinc-800 lg:w-[420px] lg:max-w-[480px] ${
            mobileView === "preview" ? "hidden lg:flex" : "flex"
          }`}
        >
          {selectedIssue ? (
            <ResumeFixDrawer
              issue={selectedIssue}
              onClose={() => setSelectedIssue(null)}
              onApplySuggestion={handleApplySuggestion}
              onDismiss={handleDismiss}
              onMarkNotHelpful={handleMarkNotHelpful}
            />
          ) : (
            <ResumeIssuePanel
              issues={visibleIssues}
              selectedIssueId={selectedIssue ? (selectedIssue as ReviewIssue).id : null}
              onSelectIssue={handleSelectIssue}
            />
          )}
        </div>
      </div>
    </div>
  );
}
