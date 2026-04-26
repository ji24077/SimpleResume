"use client";

import Link from "next/link";
import { useCallback, useState, useRef } from "react";
import type { ReviewResponse } from "@/lib/types";
import ReviewWorkspace from "@/components/resume-review/ReviewWorkspace";

export default function ResumeReviewPage() {
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"file" | "text">("file");
  const [pasteText, setPasteText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);

      // Create PDF URL from the file if it's a PDF
      if (file.type === "application/pdf") {
        setPdfUrl(URL.createObjectURL(file));
      }

      const res = await fetch("/api/resume-review", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server error ${res.status}`);
      }
      const data: ReviewResponse = await res.json();
      setReview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze resume.");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTextSubmit = useCallback(async () => {
    if (!pasteText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/resume-review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: pasteText }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server error ${res.status}`);
      }
      const data: ReviewResponse = await res.json();
      setReview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze resume.");
    } finally {
      setLoading(false);
    }
  }, [pasteText]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) handleFileUpload(file);
    },
    [handleFileUpload]
  );

  const reset = useCallback(() => {
    setReview(null);
    setPdfUrl(null);
    setError(null);
    setPasteText("");
  }, []);

  if (review) {
    return (
      <div className="h-screen flex flex-col">
        {/* Thin nav bar above workspace */}
        <div className="shrink-0 flex items-center gap-3 border-b border-zinc-800 bg-zinc-950 px-4 py-2">
          <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-300">
            SimpleResume
          </Link>
          <span className="text-zinc-700">/</span>
          <span className="text-xs font-medium text-zinc-300">Resume Review</span>
          <button
            type="button"
            onClick={reset}
            className="ml-auto rounded-md border border-zinc-700 px-2.5 py-1 text-[11px] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          >
            Review Another
          </button>
        </div>
        <div className="flex-1 overflow-hidden">
          <ReviewWorkspace review={review} pdfUrl={pdfUrl} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight text-white">Resume Review</h1>
            <Link
              href="/"
              className="rounded-lg border border-zinc-700 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:border-emerald-700 hover:text-emerald-300"
            >
              Resume Generator
            </Link>
            <Link
              href="/resume-score"
              className="rounded-lg border border-zinc-700 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:border-sky-700 hover:text-sky-300"
            >
              Resume Score
            </Link>
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            Document-first review · Click issues to see exactly where they are · Get actionable fixes
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-10">
        {/* Hero */}
        <section className="relative overflow-hidden rounded-3xl border border-zinc-800/80 bg-gradient-to-b from-zinc-900/90 to-zinc-950 px-6 py-12 md:px-10 md:py-16">
          <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-sky-500/10 blur-3xl" aria-hidden />
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-500/90">
            Code-review style · Document annotations
          </p>
          <h2 className="mt-3 max-w-3xl text-3xl font-bold leading-tight tracking-tight text-white md:text-4xl">
            Review your resume like a{" "}
            <span className="bg-gradient-to-r from-sky-300 to-sky-500 bg-clip-text text-transparent">
              pull request
            </span>
          </h2>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-zinc-400 md:text-lg">
            See exactly where each problem is, why it matters, and how to fix it.
            Not just a score — an interactive review workspace.
          </p>
        </section>

        {/* Upload area */}
        <section className="mt-10 space-y-6">
          {/* Mode toggle */}
          <div className="flex gap-1 rounded-lg bg-zinc-900 p-1">
            <button
              type="button"
              onClick={() => setInputMode("file")}
              className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition ${
                inputMode === "file" ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              Upload PDF
            </button>
            <button
              type="button"
              onClick={() => setInputMode("text")}
              className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition ${
                inputMode === "text" ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              Paste Text
            </button>
          </div>

          {inputMode === "file" ? (
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              className="flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-zinc-700 bg-zinc-900/30 p-12 transition hover:border-sky-700/50 hover:bg-zinc-900/50"
            >
              <div className="text-4xl text-zinc-700" aria-hidden>↑</div>
              <p className="text-sm text-zinc-400">Drag & drop your resume PDF here</p>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={loading}
                className="rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
              >
                {loading ? "Analyzing…" : "Choose File"}
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.txt"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileUpload(f);
                }}
              />
              <p className="text-[11px] text-zinc-600">PDF or plain text. Processed locally via your backend.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                rows={12}
                className="w-full rounded-xl border border-zinc-700 bg-zinc-900/60 p-4 text-sm text-zinc-300 placeholder-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600/30 resize-none"
                placeholder="Paste your resume text here…"
              />
              <button
                type="button"
                onClick={handleTextSubmit}
                disabled={loading || !pasteText.trim()}
                className="rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
              >
                {loading ? "Analyzing…" : "Analyze Resume"}
              </button>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-sky-500 border-t-transparent" />
              <p className="text-sm text-zinc-400">Analyzing your resume — scoring, ATS check, bullet analysis…</p>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="rounded-xl border border-red-900/50 bg-red-950/30 p-4">
              <p className="text-sm text-red-300">{error}</p>
              <button
                type="button"
                onClick={() => setError(null)}
                className="mt-2 text-xs text-red-400 hover:underline"
              >
                Dismiss
              </button>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
