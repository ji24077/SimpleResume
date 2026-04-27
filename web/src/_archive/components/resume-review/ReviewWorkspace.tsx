"use client";

import { useState, useCallback } from "react";
import type { ReviewResponse, ReviewIssue } from "@/lib/types";
import ResumeScoreHeader from "./ResumeScoreHeader";
import PdfAnnotationViewer from "./PdfAnnotationViewer";
import AnnotatedResume from "./AnnotatedResume";
import CommentPanel from "./CommentPanel";
import ResumeFixDrawer from "./ResumeFixDrawer";

interface ReviewWorkspaceProps {
  review: ReviewResponse;
  pdfUrl: string | null;
}

export default function ReviewWorkspace({ review, pdfUrl }: ReviewWorkspaceProps) {
  const [selectedIssue, setSelectedIssue] = useState<ReviewIssue | null>(null);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [mobileView, setMobileView] = useState<"preview" | "comments">("preview");

  const visibleIssues = review.issues.filter((i) => !dismissedIds.has(i.id));

  const handleSelectIssue = useCallback((issue: ReviewIssue) => {
    setSelectedIssue((prev) => (prev?.id === issue.id ? null : issue));
  }, []);

  const handleFixTopIssues = useCallback(() => {
    const first = visibleIssues.find((i) => i.severity === "critical") || visibleIssues[0];
    if (first) setSelectedIssue(first);
  }, [visibleIssues]);

  const handleApplySuggestion = useCallback((issue: ReviewIssue) => {
    // TODO: integrate with resume editing
    console.log("Apply suggestion for:", issue.id);
    setDismissedIds((prev) => new Set([...prev, issue.id]));
    setSelectedIssue(null);
  }, []);

  const handleDismiss = useCallback((issue: ReviewIssue) => {
    setDismissedIds((prev) => new Set([...prev, issue.id]));
    setSelectedIssue(null);
  }, []);

  const handleMarkNotHelpful = useCallback((issue: ReviewIssue) => {
    console.log("Marked not helpful:", issue.id);
    setDismissedIds((prev) => new Set([...prev, issue.id]));
    setSelectedIssue(null);
  }, []);

  return (
    <div className="flex h-full flex-col bg-zinc-950 text-zinc-100">
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
          onClick={() => setMobileView("preview")}
          className={`flex-1 py-2.5 text-center text-xs font-medium transition ${
            mobileView === "preview" ? "bg-zinc-900 text-white" : "text-zinc-500"
          }`}
        >
          Resume
        </button>
        <button
          type="button"
          onClick={() => setMobileView("comments")}
          className={`flex-1 py-2.5 text-center text-xs font-medium transition ${
            mobileView === "comments" ? "bg-zinc-900 text-white" : "text-zinc-500"
          }`}
        >
          Comments ({visibleIssues.length})
        </button>
      </div>

      {/* Main workspace: left = PDF with highlights, right = comments panel */}
      <div className="flex flex-1 overflow-hidden">
        {/* PDF preview with highlights (left) */}
        <div className={`flex-1 overflow-hidden ${mobileView === "comments" ? "hidden lg:block" : ""}`}>
          {pdfUrl ? (
            <PdfAnnotationViewer
              pdfUrl={pdfUrl}
              issues={visibleIssues}
              selectedIssueId={selectedIssue?.id ?? null}
              onSelectIssue={handleSelectIssue}
            />
          ) : (
            <div className="h-full p-3">
              <AnnotatedResume
                sections={review.sections}
                issues={visibleIssues}
                selectedIssueId={selectedIssue?.id ?? null}
                onClickIssue={handleSelectIssue}
                pdfUrl={null}
              />
            </div>
          )}
        </div>

        {/* Right panel: comments or fix drawer */}
        <div
          className={`flex w-full flex-col overflow-hidden border-l border-zinc-800 lg:w-[380px] lg:max-w-[420px] ${
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
            <CommentPanel
              issues={visibleIssues}
              selectedIssueId={selectedIssue ? (selectedIssue as ReviewIssue).id : null}
              onSelectIssue={handleSelectIssue}
              onDismiss={handleDismiss}
            />
          )}
        </div>
      </div>
    </div>
  );
}
