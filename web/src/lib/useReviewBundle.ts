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
  /** Swap the in-memory PDF (e.g. after Apply re-renders via /api/render-only). */
  replacePdf: (blob: Blob) => void;
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
  replacePdf: () => {},
};

const KIND_LABEL: Record<string, string> = {
  experience: "EXPERIENCE",
  education: "EDUCATION",
  project: "PROJECTS",
  projects: "PROJECTS",
  skills: "SKILLS",
  summary: "SUMMARY",
};

function buildPlainTextResume(g: GenerateResponse): string {
  const parts: string[] = [];
  let lastLabel = "";
  for (const sec of g.preview_sections) {
    const label = KIND_LABEL[sec.kind.toLowerCase()] ?? sec.kind.toUpperCase();
    if (label !== lastLabel) {
      parts.push("");
      parts.push(label);
      lastLabel = label;
    }
    if (sec.title) parts.push(sec.title);
    if (sec.subtitle) parts.push(sec.subtitle);
    for (const b of sec.bullets) parts.push(`- ${b}`);
    parts.push("");
  }
  const text = parts.join("\n").trim();
  if (text) return text;
  // Fall back to extracting plaintext from the LaTeX document — strips macros and braces
  // so the score/review parser still sees Education/Experience/Skills section headers.
  return latexToPlainText(g.latex_document);
}

const SECTION_HEAD_RE = /\\section\*?\{([^}]+)\}/g;
const RESUME_ITEM_RE = /\\resumeItem\{([\s\S]*?)\}\s*(?=\\resumeItem|\\resumeItemListEnd)/g;
const SUBHEADING_RE = /\\resumeSubheading\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}/g;
const PROJECT_HEADING_RE = /\\resumeProjectHeading\{([\s\S]*?)\}\{([^}]*)\}/g;

function stripMacros(s: string): string {
  return s
    .replace(/\\textbf\{([^}]*)\}/g, "$1")
    .replace(/\\textit\{([^}]*)\}/g, "$1")
    .replace(/\\href\{[^}]*\}\{([^}]*)\}/g, "$1")
    .replace(/\\\\/g, " ")
    .replace(/\\[a-zA-Z]+\*?/g, " ")
    .replace(/[{}]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function latexToPlainText(latex: string): string {
  if (!latex) return "";
  // Slice out everything between \begin{document} and \end{document}
  const m = /\\begin\{document\}([\s\S]*?)\\end\{document\}/.exec(latex);
  const body = m ? m[1] : latex;
  const out: string[] = [];

  // Walk \section{X} headers in order; emit them uppercased so the parser recognizes them
  let match: RegExpExecArray | null;
  const headerLocations: Array<{ idx: number; name: string }> = [];
  SECTION_HEAD_RE.lastIndex = 0;
  while ((match = SECTION_HEAD_RE.exec(body)) !== null) {
    headerLocations.push({ idx: match.index, name: stripMacros(match[1]).toUpperCase() });
  }

  // Pre-section header text (centered name + contact block)
  if (headerLocations.length > 0) {
    const headerText = stripMacros(body.slice(0, headerLocations[0].idx));
    if (headerText) out.push(headerText);
  }

  for (let i = 0; i < headerLocations.length; i++) {
    const { name, idx } = headerLocations[i];
    const nextIdx = i + 1 < headerLocations.length ? headerLocations[i + 1].idx : body.length;
    const slice = body.slice(idx, nextIdx);
    out.push("");
    out.push(name);
    // Subheadings (Education / Experience entries)
    SUBHEADING_RE.lastIndex = 0;
    while ((match = SUBHEADING_RE.exec(slice)) !== null) {
      const [, role, date, sub, loc] = match;
      out.push(`${stripMacros(role)} — ${stripMacros(date)}`);
      if (sub || loc) out.push(`${stripMacros(sub)} ${stripMacros(loc)}`.trim());
    }
    PROJECT_HEADING_RE.lastIndex = 0;
    while ((match = PROJECT_HEADING_RE.exec(slice)) !== null) {
      out.push(stripMacros(match[1]));
    }
    RESUME_ITEM_RE.lastIndex = 0;
    while ((match = RESUME_ITEM_RE.exec(slice)) !== null) {
      out.push(`- ${stripMacros(match[1])}`);
    }
    // Fallback: if no specific macros matched, dump stripped text for that section
    if (out[out.length - 1] === name) {
      out.push(stripMacros(slice.replace(SECTION_HEAD_RE, "")));
    }
  }

  return out.join("\n").trim() || stripMacros(body);
}

export function useReviewBundle({ generate, rawText }: Args): ReviewBundle {
  const [state, setState] = useState<ReviewBundle>(EMPTY);
  const cancelledRef = useRef(false);
  const fetchedKeyRef = useRef<string | null>(null);
  const externalPdfUrlRef = useRef<string | null>(null);

  const replacePdf = useRef((blob: Blob) => {
    const url = URL.createObjectURL(blob);
    if (externalPdfUrlRef.current) URL.revokeObjectURL(externalPdfUrlRef.current);
    externalPdfUrlRef.current = url;
    setState((s) => ({ ...s, pdfBlob: blob, pdfUrl: url, pdfStatus: "ready", pdfError: null }));
  }).current;

  // Stable key — same résumé regardless of session re-hydration object identity
  const latex = generate?.latex_document ?? "";
  const key = latex ? `${latex.length}:${latex.slice(0, 64)}:${latex.slice(-64)}` : "";

  useEffect(() => {
    cancelledRef.current = false;

    if (!latex) {
      setState(EMPTY);
      return;
    }
    if (fetchedKeyRef.current === key) return; // already fetched this résumé
    fetchedKeyRef.current = key;

    let pdfObjectUrl: string | null = null;
    setState({
      ...EMPTY,
      pdfStatus: "loading",
      scoreStatus: "loading",
      reviewStatus: "loading",
      replacePdf,
    });

    // 1. Compile PDF
    fetch("/api/compile-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latex_document: latex, heal_with_llm: true }),
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

    // 2. Score (uses plain text reconstruction of generated bullets, fallback to LaTeX strip)
    const text =
      rawText && rawText.trim().length > 80
        ? rawText
        : generate
          ? buildPlainTextResume(generate)
          : "";
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
    // Intentionally key on the stable hash, not the generate object identity
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, rawText]);

  return state;
}
