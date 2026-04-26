"use client";

import { useEffect, useRef, useState } from "react";
import type { GenerateResponse, ResumeScoreResponse, ReviewResponse } from "@/lib/types";

export type BundleStatus = "idle" | "loading" | "ready" | "error";

export type ReviewBundle = {
  pdfUrl: string | null;
  pdfBlob: Blob | null;
  pdfError: string | null;
  pdfStatus: BundleStatus;
  score: ResumeScoreResponse | null;
  scoreError: string | null;
  scoreStatus: BundleStatus;
  review: ReviewResponse | null;
  reviewError: string | null;
  reviewStatus: BundleStatus;
};

type Args = {
  generate: GenerateResponse | null;
  rawText: string | null;
};

const EMPTY: ReviewBundle = {
  pdfUrl: null,
  pdfBlob: null,
  pdfError: null,
  pdfStatus: "idle",
  score: null,
  scoreError: null,
  scoreStatus: "idle",
  review: null,
  reviewError: null,
  reviewStatus: "idle",
};

function buildPlainTextResume(g: GenerateResponse): string {
  const parts: string[] = [];
  for (const sec of g.preview_sections) {
    parts.push(sec.title);
    if (sec.subtitle) parts.push(sec.subtitle);
    for (const b of sec.bullets) parts.push(`- ${b}`);
    parts.push("");
  }
  return parts.join("\n");
}

export function useReviewBundle({ generate, rawText }: Args): ReviewBundle {
  const [state, setState] = useState<ReviewBundle>(EMPTY);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;

    if (!generate?.latex_document) {
      setState(EMPTY);
      return;
    }

    let pdfObjectUrl: string | null = null;
    setState({
      ...EMPTY,
      pdfStatus: "loading",
      scoreStatus: "loading",
      reviewStatus: "loading",
    });

    // 1. Compile PDF
    fetch("/api/compile-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latex_document: generate.latex_document, heal_with_llm: true }),
    })
      .then(async (res) => {
        if (cancelledRef.current) return;
        if (!res.ok) {
          const j = await res.json().catch(() => ({}));
          setState((s) => ({
            ...s,
            pdfStatus: "error",
            pdfError: typeof j.detail === "string" ? j.detail : "PDF compile failed",
          }));
          return;
        }
        const blob = await res.blob();
        if (cancelledRef.current) return;
        pdfObjectUrl = URL.createObjectURL(blob);
        setState((s) => ({
          ...s,
          pdfStatus: "ready",
          pdfBlob: blob,
          pdfUrl: pdfObjectUrl,
        }));
      })
      .catch(() => {
        if (cancelledRef.current) return;
        setState((s) => ({ ...s, pdfStatus: "error", pdfError: "Network error compiling PDF" }));
      });

    // 2. Score (uses plain text reconstruction of generated bullets)
    const text = rawText && rawText.trim().length > 80 ? rawText : buildPlainTextResume(generate);
    fetch("/api/resume-score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
      .then(async (res) => {
        if (cancelledRef.current) return;
        if (!res.ok) {
          setState((s) => ({ ...s, scoreStatus: "error", scoreError: `Score failed (${res.status})` }));
          return;
        }
        const data = (await res.json()) as ResumeScoreResponse;
        setState((s) => ({ ...s, scoreStatus: "ready", score: data }));
      })
      .catch(() => {
        if (cancelledRef.current) return;
        setState((s) => ({ ...s, scoreStatus: "error", scoreError: "Network error scoring" }));
      });

    // 3. Review (issues with bboxes for PDF highlights)
    fetch("/api/resume-review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
      .then(async (res) => {
        if (cancelledRef.current) return;
        if (!res.ok) {
          setState((s) => ({ ...s, reviewStatus: "error", reviewError: `Review failed (${res.status})` }));
          return;
        }
        const data = (await res.json()) as ReviewResponse;
        setState((s) => ({ ...s, reviewStatus: "ready", review: data }));
      })
      .catch(() => {
        if (cancelledRef.current) return;
        setState((s) => ({ ...s, reviewStatus: "error", reviewError: "Network error reviewing" }));
      });

    return () => {
      cancelledRef.current = true;
      if (pdfObjectUrl) URL.revokeObjectURL(pdfObjectUrl);
    };
  }, [generate, rawText]);

  return state;
}
