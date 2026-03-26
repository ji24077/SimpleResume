"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import type { GenerateResponse } from "@/lib/types";

const PdfJsPreview = dynamic(() => import("@/components/PdfJsPreview"), {
  ssr: false,
  loading: () => <p className="py-8 text-center text-sm text-zinc-500">Loading PDF viewer…</p>,
});

type BackendHealth = {
  ok?: boolean;
  openai_configured?: boolean;
  env_hint?: string;
  error?: string;
  pdf_compile?: boolean;
  compiler?: {
    latexmk?: boolean;
    latex_docker_ready?: boolean;
    latex_docker_image?: string | null;
    docker?: boolean;
  };
};

const KIND_LABEL: Record<string, string> = {
  education: "Education",
  experience: "Experience",
  project: "Project",
  skills: "Skills",
  summary: "Summary",
};

function downloadTex(latex: string, filename = "resume.tex") {
  const blob = new Blob([latex], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function downloadPdfBlob(blob: Blob, filename = "resume.pdf") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function downloadCoachingMd(data: GenerateResponse) {
  const lines: string[] = ["# Resume coaching\n"];
  data.preview_sections.forEach((sec, i) => {
    const coach = data.coaching[i];
    const label = KIND_LABEL[sec.kind] || sec.kind;
    lines.push(`## ${label}: ${sec.title}`);
    if (sec.subtitle) lines.push(`*${sec.subtitle}*\n`);
    if (coach?.section_why) {
      lines.push(`### Why this section works\n${coach.section_why}\n`);
    }
    sec.bullets.forEach((b, j) => {
      lines.push(`- **Bullet:** ${b}`);
      const w = coach?.items[j]?.why_better;
      if (w) lines.push(`  - *Why stronger:* ${w}`);
    });
    lines.push("");
  });
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "resume-coaching.md";
  a.click();
  URL.revokeObjectURL(a.href);
}

const EMPTY_LATEX_SHELL: GenerateResponse = {
  latex_document: "",
  preview_sections: [],
  coaching: [],
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [paste, setPaste] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  /** Working copy edited in the LaTeX tab; sent to /compile-pdf when Compile runs */
  const [latexDraft, setLatexDraft] = useState("");
  const latexDraftRef = useRef("");
  const [tab, setTab] = useState<"preview" | "coaching" | "latex">("preview");
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [showTextPreview, setShowTextPreview] = useState(false);
  /** Bump to compile current latexDraft (Overleaf-style manual build) */
  const [compileNonce, setCompileNonce] = useState(0);
  const [latexOnlyBootstrap, setLatexOnlyBootstrap] = useState("");

  useEffect(() => {
    latexDraftRef.current = latexDraft;
  }, [latexDraft]);

  useEffect(() => {
    fetch("/api/backend-health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ok: false, error: "Health check failed" }));
  }, []);

  useEffect(() => {
    if (compileNonce === 0) {
      return;
    }
    const source = latexDraftRef.current;
    if (!source.trim()) {
      setPdfLoading(false);
      setPdfError("LaTeX is empty. Paste or generate a document, then Compile.");
      setPdfUrl(null);
      setPdfBlob(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;
    setPdfLoading(true);
    setPdfError(null);
    setPdfUrl(null);
    setPdfBlob(null);

    fetch("/api/compile-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latex_document: source }),
    })
      .then(async (res) => {
        if (cancelled) return;
        if (!res.ok) {
          const j = await res.json().catch(() => ({}));
          setPdfError(
            typeof j.detail === "string"
              ? j.detail
              : JSON.stringify(j.detail ?? {}, null, 2)
          );
          return;
        }
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPdfBlob(blob);
        setPdfUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setPdfError("Network error compiling PDF");
      })
      .finally(() => {
        if (!cancelled) setPdfLoading(false);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [compileNonce]);

  const canSubmit = Boolean(file || paste.trim());

  const onSubmit = useCallback(async () => {
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      let res: Response;
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        res = await fetch("/api/generate", { method: "POST", body: fd });
      } else {
        res = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: paste }),
        });
      }
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail || json) || res.statusText);
        return;
      }
      const gen = json as GenerateResponse;
      setResult(gen);
      setLatexDraft(gen.latex_document);
      latexDraftRef.current = gen.latex_document;
      setCompileNonce((n) => n + 1);
      setTab("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [file, paste]);

  const reset = () => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
    setPdfBlob(null);
    setPdfError(null);
    setResult(null);
    setLatexDraft("");
    latexDraftRef.current = "";
    setCompileNonce(0);
    setFile(null);
    setPaste("");
    setError(null);
    setLatexOnlyBootstrap("");
  };

  const runCompile = useCallback(() => {
    setCompileNonce((n) => n + 1);
  }, []);

  const startLatexOnly = useCallback(() => {
    const t = latexOnlyBootstrap.trim();
    if (!t) {
      setError("Paste a full LaTeX source first.");
      return;
    }
    if (!t.includes("\\documentclass")) {
      setError("LaTeX must include \\documentclass{...}.");
      return;
    }
    setError(null);
    latexDraftRef.current = t;
    setLatexDraft(t);
    setResult({
      ...EMPTY_LATEX_SHELL,
      latex_document: t,
    });
    setCompileNonce((n) => n + 1);
    setTab("preview");
  }, [latexOnlyBootstrap]);

  const isLatexOnlySession =
    result != null && result.preview_sections.length === 0 && result.coaching.length === 0;
  const draftDiffersFromSaved = result != null && latexDraft !== result.latex_document;

  const resumeBuilderRef = useRef<HTMLDivElement>(null);
  const scrollToResumeBuilder = useCallback(() => {
    resumeBuilderRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-white">SimpleResume</h1>
              <p className="text-xs text-zinc-500">Big Tech–ready resumes · LaTeX · coaching</p>
            </div>
            {health && (
              <div className="max-w-md text-right text-xs">
                {!health.ok && (
                  <p className="rounded-lg bg-red-950/60 px-2 py-1 text-red-300">
                    API 연결 실패: 터미널에서{" "}
                    <code className="rounded bg-zinc-800 px-1">cd api && uvicorn main:app --reload --port 8000</code>
                    {health.error ? ` — ${health.error}` : ""}
                  </p>
                )}
                {health.ok && !health.openai_configured && (
                  <p className="rounded-lg bg-amber-950/60 px-2 py-1 text-amber-200">
                    <strong>OpenAI 미설정:</strong>{" "}
                    <code className="rounded bg-zinc-800 px-1">{health.env_hint || "api/.env"}</code> 파일에{" "}
                    <code className="rounded bg-zinc-800 px-1">OPENAI_API_KEY=sk-...</code> 넣고 API 서버를{" "}
                    <strong>재시작</strong>하세요.
                  </p>
                )}
                {health.ok && health.openai_configured && (
                  <p className="text-emerald-500/90">
                    API · OpenAI 연결됨
                    {health.compiler?.latex_docker_ready && (
                      <span className="ml-2 text-zinc-500">
                        · PDF: Docker (
                        <code className="rounded bg-zinc-800 px-1">{health.compiler.latex_docker_image}</code>)
                      </span>
                    )}
                    {health.compiler && !health.compiler.latex_docker_ready && health.compiler.latexmk && (
                      <span className="ml-2 text-zinc-500">· PDF: latexmk</span>
                    )}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-10">
        {!result ? (
          <div className="space-y-12">
            <section
              className="relative overflow-hidden rounded-3xl border border-zinc-800/80 bg-gradient-to-b from-zinc-900/90 to-zinc-950 px-6 py-12 md:px-10 md:py-16"
              aria-labelledby="hero-heading"
            >
              <div
                className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl"
                aria-hidden
              />
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-500/90">
                Recruiter-tested · SWE / infra
              </p>
              <h2
                id="hero-heading"
                className="mt-3 max-w-3xl text-3xl font-bold leading-tight tracking-tight text-white md:text-4xl md:leading-tight"
              >
                Make sure your resume is{" "}
                <span className="bg-gradient-to-r from-emerald-300 to-emerald-500 bg-clip-text text-transparent">
                  Big Tech–ready
                </span>
              </h2>
              <p className="mt-5 max-w-2xl text-base leading-relaxed text-zinc-400 md:text-lg">
                Your draft is <strong className="text-zinc-200">analyzed</strong> and rewritten into scannable
                bullets, Dhruv-style LaTeX, section coaching, and a live PDF preview — the same bar we use for
                top-tier hiring loops.
              </p>
              <ul className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:gap-4">
                <li className="inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-200">
                  <span className="text-emerald-400" aria-hidden>
                    ✓
                  </span>
                  <span>
                    <strong className="font-semibold text-white">30+</strong> candidates coached toward interviews
                  </span>
                </li>
                <li className="inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-200">
                  <span className="text-emerald-400" aria-hidden>
                    ✓
                  </span>
                  Metrics, stack, and outcomes — not generic filler
                </li>
                <li className="inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-200">
                  <span className="text-emerald-400" aria-hidden>
                    ✓
                  </span>
                  Export <strong className="font-semibold text-white">.tex</strong>, coaching{" "}
                  <strong className="font-semibold text-white">.md</strong>, PDF
                </li>
              </ul>
              <div className="mt-10 flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={scrollToResumeBuilder}
                  className="inline-flex items-center justify-center rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-emerald-950 shadow-lg shadow-emerald-900/30 transition hover:bg-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-zinc-950"
                >
                  Build your resume
                </button>
                <button
                  type="button"
                  onClick={scrollToResumeBuilder}
                  className="text-sm font-medium text-zinc-400 underline-offset-4 transition hover:text-zinc-200 hover:underline"
                >
                  Upload, paste, or paste LaTeX below →
                </button>
              </div>
            </section>

            <div ref={resumeBuilderRef} id="resume-builder" className="scroll-mt-6 space-y-8">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-8">
              <h2 className="mb-2 text-sm font-medium text-zinc-300">1. Upload or paste</h2>
              <p className="mb-6 text-sm text-zinc-500">
                PDF, .tex, or .txt — we extract text and rewrite to high-readability bullets + full LaTeX.
              </p>
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-zinc-700 bg-zinc-900 px-6 py-12 transition hover:border-emerald-600/50 hover:bg-zinc-800/50">
                <input
                  type="file"
                  accept=".pdf,.tex,.txt"
                  className="hidden"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] ?? null);
                    setError(null);
                  }}
                />
                <span className="text-sm text-zinc-400">
                  {file ? file.name : "Drop file or click to choose"}
                </span>
              </label>
              <p className="mt-4 text-center text-xs text-zinc-600">or</p>
              <textarea
                value={paste}
                onChange={(e) => {
                  setPaste(e.target.value);
                  if (e.target.value) setFile(null);
                  setError(null);
                }}
                placeholder="Paste resume text here…"
                rows={10}
                className="mt-4 w-full resize-y rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
              />
              {error && (
                <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-sm text-red-300">{error}</p>
              )}
              <button
                type="button"
                disabled={!canSubmit || loading}
                onClick={onSubmit}
                className="mt-6 w-full rounded-xl bg-emerald-600 py-3 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {loading ? "Generating… (can take 30–90s)" : "Generate resume"}
              </button>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-8">
              <h2 className="mb-2 text-sm font-medium text-zinc-300">2. Or: LaTeX only (Overleaf-style)</h2>
              <p className="mb-4 text-sm text-zinc-500">
                Paste a complete <code className="rounded bg-zinc-800 px-1">.tex</code> file, then <strong>Compile</strong>{" "}
                for PDF preview — no AI step.
              </p>
              <textarea
                value={latexOnlyBootstrap}
                onChange={(e) => {
                  setLatexOnlyBootstrap(e.target.value);
                  setError(null);
                }}
                spellCheck={false}
                placeholder="% Paste full LaTeX here (must include \\documentclass)…"
                rows={12}
                className="w-full resize-y rounded-xl border border-zinc-700 bg-zinc-950 px-4 py-3 font-mono text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-amber-600 focus:outline-none focus:ring-1 focus:ring-amber-600"
              />
              <button
                type="button"
                onClick={startLatexOnly}
                disabled={!latexOnlyBootstrap.trim()}
                className="mt-4 w-full rounded-xl border border-amber-700 bg-amber-950/40 py-3 text-sm font-medium text-amber-200 transition hover:bg-amber-950/70 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Open editor &amp; compile
              </button>
            </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={reset}
                className="rounded-lg border border-zinc-600 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800"
              >
                New upload
              </button>
              <button
                type="button"
                onClick={() => downloadTex(latexDraft || result.latex_document)}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500"
              >
                Download .tex
              </button>
              {pdfBlob && (
                <button
                  type="button"
                  onClick={() => downloadPdfBlob(pdfBlob)}
                  className="rounded-lg border border-zinc-500 px-3 py-1.5 text-sm text-zinc-200 hover:bg-zinc-800"
                >
                  Download PDF
                </button>
              )}
              {!isLatexOnlySession && (
                <button
                  type="button"
                  onClick={() => downloadCoachingMd(result)}
                  className="rounded-lg border border-emerald-700 px-3 py-1.5 text-sm text-emerald-400 hover:bg-emerald-950/50"
                >
                  Download coaching (.md)
                </button>
              )}
            </div>

            <div className="flex gap-1 rounded-lg bg-zinc-900 p-1">
              {(["preview", "coaching", "latex"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTab(t)}
                  disabled={isLatexOnlySession && t === "coaching"}
                  className={`flex-1 rounded-md py-2 text-sm font-medium capitalize transition ${
                    tab === t ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
                  } ${isLatexOnlySession && t === "coaching" ? "cursor-not-allowed opacity-40" : ""}`}
                >
                  {t === "latex" ? "LaTeX" : t}
                </button>
              ))}
            </div>

            {tab === "preview" && (
              <div className="space-y-4 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-zinc-300">
                    PDF preview — edit in <strong className="text-zinc-200">LaTeX</strong> tab, then{" "}
                    <strong className="text-amber-300">Compile</strong> (Overleaf-style)
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={runCompile}
                      disabled={pdfLoading || !latexDraft.trim()}
                      className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-amber-950 hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      Compile
                    </button>
                    {!isLatexOnlySession && (
                      <button
                        type="button"
                        onClick={() => setShowTextPreview((v) => !v)}
                        className="text-xs text-emerald-400 hover:underline"
                      >
                        {showTextPreview ? "Hide text list" : "Show plain text list"}
                      </button>
                    )}
                  </div>
                </div>
                {pdfLoading && (
                  <p className="text-sm text-zinc-500">Compiling PDF… (first run may take 10–30s)</p>
                )}
                {pdfError && (
                  <div className="rounded-lg border border-amber-900/50 bg-amber-950/30 p-4 text-sm text-amber-100">
                    <p className="font-medium text-amber-200">PDF 미리보기 불가</p>
                    <p className="mt-2 whitespace-pre-wrap font-mono text-xs text-zinc-400">{pdfError.slice(0, 2000)}</p>
                    <p className="mt-3 text-xs text-zinc-500">
                      권장: <code className="rounded bg-zinc-800 px-1">docker compose build texlive</code> 후{" "}
                      <code className="rounded bg-zinc-800 px-1">LATEX_DOCKER_IMAGE=simpleresume-texlive:full</code> 로 API
                      실행. 또는 MacTeX/latexmk. README 참고.
                    </p>
                  </div>
                )}
                {pdfUrl && !pdfLoading && (
                  <div className="space-y-2">
                    <PdfJsPreview fileUrl={pdfUrl} />
                    <p className="text-center text-[10px] text-zinc-600">
                      <a
                        href={pdfUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-emerald-500/90 underline hover:text-emerald-400"
                      >
                        Open PDF in new tab
                      </a>
                    </p>
                  </div>
                )}
                {showTextPreview && !isLatexOnlySession && (
                  <div className="mt-6 space-y-6 border-t border-zinc-800 pt-6">
                    <p className="text-xs text-zinc-500">Plain bullet list (no LaTeX layout)</p>
                    {result.preview_sections.map((sec, i) => (
                      <section key={i} className="border-b border-zinc-800 pb-6 last:border-0">
                        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-500/90">
                          {KIND_LABEL[sec.kind] || sec.kind}
                        </div>
                        <h3 className="text-base font-semibold text-white">{sec.title}</h3>
                        {sec.subtitle && <p className="text-sm italic text-zinc-400">{sec.subtitle}</p>}
                        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-zinc-300">
                          {sec.bullets.map((b, j) => (
                            <li key={j}>{b}</li>
                          ))}
                        </ul>
                      </section>
                    ))}
                  </div>
                )}
                {showTextPreview && isLatexOnlySession && (
                  <p className="mt-4 text-xs text-zinc-600">Plain-text list is available after AI Generate (not in LaTeX-only mode).</p>
                )}
              </div>
            )}

            {tab === "coaching" && (
              <div className="space-y-8 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
                {isLatexOnlySession ? (
                  <p className="text-sm text-zinc-500">
                    Coaching appears when you use <strong className="text-zinc-400">Generate resume</strong>. LaTeX-only
                    mode is compile + preview only.
                  </p>
                ) : (
                  <>
                <p className="text-sm text-zinc-400">
                  Why each section and bullet is stronger — recruiter scan + credibility.
                </p>
                {result.preview_sections.map((sec, i) => {
                  const coach = result.coaching[i];
                  return (
                    <section key={i} className="border-b border-zinc-800 pb-8 last:border-0 last:pb-0">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-amber-500/90">
                        {KIND_LABEL[sec.kind] || sec.kind}
                      </div>
                      <h3 className="mt-1 text-base font-semibold text-white">{sec.title}</h3>
                      {coach?.section_why && (
                        <div className="mt-3 rounded-lg border border-amber-900/40 bg-amber-950/20 px-4 py-3">
                          <div className="text-xs font-medium text-amber-200/90">Why this block works</div>
                          <p className="mt-1 text-sm leading-relaxed text-zinc-300">{coach.section_why}</p>
                        </div>
                      )}
                      <ul className="mt-4 space-y-4">
                        {sec.bullets.map((b, j) => (
                          <li key={j} className="rounded-lg border border-zinc-700/60 bg-zinc-900/80 p-4">
                            <p className="text-sm text-zinc-200">{b}</p>
                            {coach?.items[j]?.why_better && (
                              <p className="mt-2 border-t border-zinc-800 pt-2 text-sm text-emerald-400/90">
                                <span className="font-medium text-emerald-500">Stronger because: </span>
                                {coach.items[j].why_better}
                              </p>
                            )}
                          </li>
                        ))}
                      </ul>
                    </section>
                  );
                })}
                  </>
                )}
              </div>
            )}

            {tab === "latex" && (
              <div className="space-y-3 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-zinc-300">Editor (full .tex)</p>
                  <div className="flex flex-wrap items-center gap-2">
                    {draftDiffersFromSaved && !isLatexOnlySession && (
                      <button
                        type="button"
                        onClick={() => {
                          setLatexDraft(result.latex_document);
                          latexDraftRef.current = result.latex_document;
                        }}
                        className="rounded-md border border-zinc-600 px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800"
                      >
                        Revert to last Generate
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={runCompile}
                      disabled={pdfLoading || !latexDraft.trim()}
                      className="rounded-md bg-amber-600 px-4 py-1.5 text-sm font-medium text-amber-950 hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {pdfLoading ? "Compiling…" : "Compile"}
                    </button>
                  </div>
                </div>
                {draftDiffersFromSaved && (
                  <p className="text-xs text-amber-200/80">
                    Unsaved edits vs. last Generate output — Compile to refresh the PDF preview.
                  </p>
                )}
                <textarea
                  value={latexDraft}
                  onChange={(e) => setLatexDraft(e.target.value)}
                  spellCheck={false}
                  className="min-h-[min(70vh,720px)] w-full resize-y rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-3 font-mono text-xs leading-relaxed text-emerald-100/90 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                  placeholder="\\documentclass{article} ..."
                />
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
