"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import type { ReviewIssue, IssueSeverity } from "@/lib/types";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const SEV_COLORS: Record<IssueSeverity, string> = {
  critical: "var(--error-bg)",
  moderate: "var(--warn-bg)",
  minor: "var(--success-bg)",
};

const SEV_BORDER: Record<IssueSeverity, string> = {
  critical: "var(--error)",
  moderate: "var(--warn)",
  minor: "var(--success)",
};

interface HighlightRect {
  issueId: string;
  severity: IssueSeverity;
  top: number;
  left: number;
  width: number;
  height: number;
}

interface PdfAnnotationViewerProps {
  pdfUrl: string;
  issues: ReviewIssue[];
  selectedIssueId: string | null;
  onSelectIssue: (issue: ReviewIssue) => void;
}

export default function PdfAnnotationViewer({
  pdfUrl,
  issues,
  selectedIssueId,
  onSelectIssue,
}: PdfAnnotationViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const [pageWidth, setPageWidth] = useState(680);
  const [highlights, setHighlights] = useState<HighlightRect[]>([]);
  const [hoveredHighlight, setHoveredHighlight] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const issueMap = useMemo(() => new Map(issues.map((i) => [i.id, i])), [issues]);

  useEffect(() => {
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width - 48;
        if (w > 200) setPageWidth(Math.min(w, 900));
      }
    });
    if (containerRef.current) obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const findHighlightsInTextLayer = useCallback(() => {
    if (!containerRef.current) return;
    const rects: HighlightRect[] = [];

    for (const issue of issues) {
      if (!issue.original_text || issue.original_text.length < 5) continue;

      const textSpans = containerRef.current.querySelectorAll(
        ".react-pdf__Page__textContent span"
      );

      const needle = issue.original_text.toLowerCase().trim();
      const needleWords = needle.split(/\s+/).filter(Boolean);
      if (needleWords.length === 0) continue;

      const firstWord = needleWords[0];
      const lastWord = needleWords[needleWords.length - 1];

      for (let si = 0; si < textSpans.length; si++) {
        const spanText = (textSpans[si].textContent || "").toLowerCase().trim();
        if (!spanText.includes(firstWord)) continue;

        let combinedText = "";
        const matchSpans: Element[] = [];

        for (let j = si; j < Math.min(si + 20, textSpans.length); j++) {
          const t = (textSpans[j].textContent || "").trim();
          if (!t) continue;
          combinedText += (combinedText ? " " : "") + t.toLowerCase();
          matchSpans.push(textSpans[j]);

          if (combinedText.includes(lastWord) && combinedText.length >= needle.length * 0.5) {
            const pageEl = textSpans[si].closest(".react-pdf__Page");
            if (!pageEl) break;
            const pageRect = pageEl.getBoundingClientRect();

            for (const ms of matchSpans) {
              const r = ms.getBoundingClientRect();
              if (r.width < 2 || r.height < 2) continue;
              rects.push({
                issueId: issue.id,
                severity: issue.severity as IssueSeverity,
                top: r.top - pageRect.top,
                left: r.left - pageRect.left,
                width: r.width,
                height: r.height,
              });
            }
            break;
          }
        }
      }
    }

    setHighlights(rects);
  }, [issues]);

  const handlePageRender = useCallback(() => {
    const timer = setTimeout(() => findHighlightsInTextLayer(), 300);
    return () => clearTimeout(timer);
  }, [findHighlightsInTextLayer]);

  useEffect(() => {
    if (!selectedIssueId || !containerRef.current) return;
    const matchHighlight = highlights.find((h) => h.issueId === selectedIssueId);
    if (matchHighlight) {
      const pages = containerRef.current.querySelectorAll(".react-pdf__Page");
      const issue = issueMap.get(selectedIssueId);
      const pageIdx = (issue?.location.page ?? 1) - 1;
      const targetPage = pages[pageIdx] || pages[0];
      if (targetPage) {
        targetPage.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }, [selectedIssueId, highlights, issueMap]);

  const groupedByPage = useMemo(() => {
    const map = new Map<number, HighlightRect[]>();
    for (const h of highlights) {
      const issue = issueMap.get(h.issueId);
      const page = issue?.location.page ?? 1;
      if (!map.has(page)) map.set(page, []);
      map.get(page)!.push(h);
    }
    return map;
  }, [highlights, issueMap]);

  return (
    <div
      className="flex h-full flex-col overflow-hidden rounded-lg"
      style={{ background: "var(--canvas-alt)", border: "1px solid var(--border)" }}
    >
      <div ref={containerRef} className="flex-1 overflow-y-auto p-6">
        <Document
          file={pdfUrl}
          onLoadSuccess={({ numPages: n }) => setNumPages(n)}
          loading={
            <div className="flex items-center justify-center py-20">
              <div
                className="h-5 w-5 animate-spin rounded-full border-2 border-t-transparent"
                style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
              />
            </div>
          }
          error={
            <div className="py-20 text-center text-sm" style={{ color: "var(--fg-4)" }}>
              Failed to load PDF. Try re-uploading.
            </div>
          }
        >
          {Array.from({ length: numPages }, (_, i) => {
            const pageNum = i + 1;
            const pageHighlights = groupedByPage.get(pageNum) || [];

            return (
              <div
                key={pageNum}
                ref={(el) => { if (el) pageRefs.current.set(pageNum, el); }}
                className="relative mx-auto mb-6 shadow-lg"
                style={{ width: pageWidth }}
              >
                <Page
                  pageNumber={pageNum}
                  width={pageWidth}
                  onRenderSuccess={() => handlePageRender()}
                  renderTextLayer={true}
                  renderAnnotationLayer={false}
                />

                {pageHighlights.map((h, idx) => {
                  const isSelected = h.issueId === selectedIssueId;
                  const isHovered = h.issueId === hoveredHighlight;
                  const issue = issueMap.get(h.issueId);

                  return (
                    <div
                      key={`${h.issueId}-${idx}`}
                      className="absolute cursor-pointer transition-all duration-150"
                      style={{
                        top: h.top,
                        left: h.left,
                        width: h.width,
                        height: h.height,
                        backgroundColor: SEV_COLORS[h.severity],
                        borderBottom: `2px solid ${SEV_BORDER[h.severity]}`,
                        outline: isSelected ? `2px solid ${SEV_BORDER[h.severity]}` : "none",
                        opacity: isSelected || isHovered ? 1 : 0.7,
                        zIndex: isSelected ? 20 : isHovered ? 15 : 10,
                        borderRadius: "2px",
                      }}
                      onClick={() => issue && onSelectIssue(issue)}
                      onMouseEnter={() => setHoveredHighlight(h.issueId)}
                      onMouseLeave={() => setHoveredHighlight(null)}
                      title={issue?.title}
                    >
                      {(isHovered || isSelected) && idx === 0 && issue && (
                        <div
                          className="pointer-events-none absolute -top-8 left-0 z-30 max-w-xs rounded-md px-2 py-1 text-[10px] font-medium leading-tight shadow-lg"
                          style={{
                            backgroundColor: SEV_BORDER[h.severity],
                            color: "white",
                          }}
                        >
                          {issue.title}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </Document>
      </div>
    </div>
  );
}
