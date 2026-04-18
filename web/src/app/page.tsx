"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { GenerateResponse, PagePolicy } from "@/lib/types";
import UploadForm from "@/components/UploadForm";
import PdfPreview from "@/components/PdfPreview";
import CoachingPanel from "@/components/CoachingPanel";
import LatexViewer from "@/components/LatexViewer";

type BackendHealth = {
  ok?: boolean;
  openai_configured?: boolean;
  env_hint?: string;
  error?: string;
  pdf_compile?: boolean;
};

const LOOKS_LIKE_EMAIL = /\S+@\S+\.\S+/;
const HAS_LINKEDIN = /linkedin\.com/i;

function pasteContactGaps(paste: string): { needEmail: boolean; needLinkedin: boolean } {
  const p = paste.trim();
  if (!p) return { needEmail: false, needLinkedin: false };
  return {
    needEmail: !LOOKS_LIKE_EMAIL.test(p),
    needLinkedin: !HAS_LINKEDIN.test(p),
  };
}

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

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [paste, setPaste] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [tab, setTab] = useState<"preview" | "coaching" | "latex">("preview");
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [showTextPreview, setShowTextPreview] = useState(false);
  const [pdfRefresh, setPdfRefresh] = useState(0);
  const [pagePolicy, setPagePolicy] = useState<PagePolicy>("strict_one_page");
  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [contactEmail, setContactEmail] = useState("");
  const [contactLinkedin, setContactLinkedin] = useState("");
  const [contactPhone, setContactPhone] = useState("");

  const resumeBuilderRef = useRef<HTMLDivElement>(null);
  const scrollToResumeBuilder = useCallback(() => {
    resumeBuilderRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  useEffect(() => {
    fetch("/api/backend-health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ok: false, error: "Health check failed" }));
  }, []);

  useEffect(() => {
    if (!result?.latex_document) {
      setPdfUrl(null);
      setPdfBlob(null);
      setPdfError(null);
      setPdfLoading(false);
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
      body: JSON.stringify({
        latex_document: result.latex_document,
        heal_with_llm: true,
      }),
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
  }, [result?.latex_document, pdfRefresh]);

  const canSubmit = Boolean(file || paste.trim());

  const onSubmit = useCallback(async () => {
    setError(null);
    setLoading(true);
    setProgressMessage(null);
    setResult(null);
    try {
      if (!file) {
        const { needEmail, needLinkedin } = pasteContactGaps(paste);
        if (needEmail && !contactEmail.trim()) {
          setError(
            "원문에서 이메일이 잘 안 보입니다. 아래 '연락처'에 이메일을 입력하거나, 원문에 주소를 적어 주세요."
          );
          setLoading(false);
          return;
        }
        if (needLinkedin && !contactLinkedin.trim()) {
          setError(
            "원문에서 LinkedIn이 잘 안 보입니다. 아래에 프로필 URL을 입력하거나, 원문에 linkedin.com 링크를 넣어 주세요."
          );
          setLoading(false);
          return;
        }
      }

      let res: Response;
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("page_policy", pagePolicy);
        fd.append("contact_email", contactEmail);
        fd.append("contact_linkedin", contactLinkedin);
        fd.append("contact_phone", contactPhone);
        res = await fetch("/api/generate-stream", { method: "POST", body: fd });
      } else {
        res = await fetch("/api/generate-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: paste,
            page_policy: pagePolicy,
            contact_email: contactEmail,
            contact_linkedin: contactLinkedin,
            contact_phone: contactPhone,
          }),
        });
      }

      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        setError(
          typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail || json) || res.statusText
        );
        return;
      }

      if (!res.body) {
        setError("Empty response from server");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalResult: GenerateResponse | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          let ev: { type?: string; message?: string; message_en?: string; data?: GenerateResponse; detail?: string };
          try {
            ev = JSON.parse(trimmed) as typeof ev;
          } catch {
            continue;
          }
          if (ev.type === "progress") {
            setProgressMessage(ev.message ?? ev.message_en ?? null);
          } else if (ev.type === "result" && ev.data) {
            finalResult = ev.data as GenerateResponse;
          } else if (ev.type === "error") {
            setError(ev.detail ?? "Generate failed");
            return;
          }
        }
      }

      const tail = buffer.trim();
      if (tail) {
        try {
          const ev = JSON.parse(tail) as {
            type?: string;
            data?: GenerateResponse;
            detail?: string;
          };
          if (ev.type === "result" && ev.data) finalResult = ev.data;
          if (ev.type === "error") {
            setError(ev.detail ?? "Generate failed");
            return;
          }
        } catch {
          /* ignore */
        }
      }

      if (!finalResult) {
        setError("No result from stream");
        return;
      }
      setResult(finalResult);
      setTab("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
      setProgressMessage(null);
    }
  }, [file, paste, pagePolicy, contactEmail, contactLinkedin, contactPhone]);

  const handleSetFile = useCallback((f: File | null) => {
    setFile(f);
    setError(null);
  }, []);

  const handleSetPaste = useCallback((v: string) => {
    setPaste(v);
    if (v) setFile(null);
    setError(null);
  }, []);

  const reset = () => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
    setPdfBlob(null);
    setPdfError(null);
    setResult(null);
    setFile(null);
    setPaste("");
    setContactEmail("");
    setContactLinkedin("");
    setContactPhone("");
    setError(null);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-lg font-semibold tracking-tight text-white">SimpleResume</h1>
                <Link
                  href="/latex"
                  className="rounded-lg border border-zinc-700 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:border-emerald-700 hover:text-emerald-300"
                >
                  Compile LaTeX only
                </Link>
                <Link
                  href="/resume-score"
                  className="rounded-lg border border-zinc-700 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:border-sky-700 hover:text-sky-300"
                >
                  Resume Score
                </Link>
              </div>
              <p className="text-xs text-zinc-500">
                100+ résumés analyzed · ATS-friendly · LaTeX + coaching
              </p>
            </div>
            {health && (
              <div className="max-w-md text-right text-xs">
                {!health.ok && (
                  <p className="rounded-lg bg-red-950/60 px-2 py-1 text-red-300">
                    API unreachable — run{" "}
                    <code className="rounded bg-zinc-800 px-1">cd api && uvicorn main:app --reload --port 8000</code>
                    {health.error ? ` — ${health.error}` : ""}
                  </p>
                )}
                {health.ok && !health.openai_configured && (
                  <p className="rounded-lg bg-amber-950/60 px-2 py-1 text-amber-200">
                    <strong>OpenAI not configured:</strong> set{" "}
                    <code className="rounded bg-zinc-800 px-1">OPENAI_API_KEY</code> in{" "}
                    <code className="rounded bg-zinc-800 px-1">{health.env_hint || "api/.env"}</code> and{" "}
                    <strong>restart</strong> the API.
                  </p>
                )}
                {health.ok && health.openai_configured && (
                  <p className="text-emerald-500/90">API &amp; OpenAI connected</p>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10">
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
                SWE &amp; infra · Recruiter-tested patterns
              </p>
              <h2
                id="hero-heading"
                className="mt-3 max-w-4xl text-3xl font-bold leading-tight tracking-tight text-white md:text-4xl md:leading-tight"
              >
                The most{" "}
                <span className="bg-gradient-to-r from-emerald-300 to-emerald-500 bg-clip-text text-transparent">
                  ATS-friendly, impactful, intuitive
                </span>{" "}
                résumé format — distilled from 100+ reviews
              </h2>
              <p className="mt-5 max-w-3xl text-base leading-relaxed text-zinc-400 md:text-lg">
                We analyzed <strong className="text-zinc-200">more than 100 résumés</strong> to extract what actually
                works: machine-readable structure for ATS, tight metrics for impact, and a layout recruiters scan in
                seconds. Your draft becomes that format — plus Dhruv-style LaTeX, section coaching, and a live PDF
                preview.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-zinc-800/80 bg-zinc-950/50 px-5 py-4">
                  <p className="text-2xl font-bold tabular-nums text-white">100+</p>
                  <p className="mt-1 text-sm text-zinc-400">Résumés reviewed to lock the ideal structure</p>
                </div>
                <div className="rounded-2xl border border-zinc-800/80 bg-zinc-950/50 px-5 py-4">
                  <p className="text-2xl font-bold tabular-nums text-emerald-400">30+</p>
                  <p className="mt-1 text-sm text-zinc-400">Candidates who advanced to interviews with this approach</p>
                </div>
                <div className="rounded-2xl border border-emerald-900/40 bg-emerald-950/20 px-5 py-4">
                  <p className="text-2xl font-bold tabular-nums text-white">~13</p>
                  <p className="mt-1 text-sm text-zinc-300">
                    Went on to offers at{" "}
                    <span className="font-medium text-emerald-200/95">
                      Amazon, IBM, DRW, Tesla, Google
                    </span>{" "}
                    and similar shops
                  </p>
                </div>
              </div>

              <ul className="mt-8 flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:gap-4">
                <li className="inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-200">
                  <span className="text-emerald-400" aria-hidden>
                    ✓
                  </span>
                  <span>
                    <strong className="font-semibold text-white">ATS-friendly</strong> — parsing-safe text &amp; structure
                  </span>
                </li>
                <li className="inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-200">
                  <span className="text-emerald-400" aria-hidden>
                    ✓
                  </span>
                  <span>
                    <strong className="font-semibold text-white">Impactful</strong> — metrics, scope, outcomes — no filler
                  </span>
                </li>
                <li className="inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-200">
                  <span className="text-emerald-400" aria-hidden>
                    ✓
                  </span>
                  <span>
                    <strong className="font-semibold text-white">Intuitive</strong> — scannable sections &amp; hierarchy
                  </span>
                </li>
                <li className="inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-200">
                  <span className="text-emerald-400" aria-hidden>
                    ✓
                  </span>
                  <span>
                    Export <strong className="font-semibold text-white">.tex</strong>, coaching{" "}
                    <strong className="font-semibold text-white">.md</strong>, PDF
                  </span>
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
                  Upload or paste below →
                </button>
              </div>
            </section>

            <div ref={resumeBuilderRef} id="resume-builder" className="scroll-mt-6 space-y-8">
              <UploadForm
                file={file}
                setFile={handleSetFile}
                paste={paste}
                setPaste={handleSetPaste}
                contactEmail={contactEmail}
                setContactEmail={setContactEmail}
                contactLinkedin={contactLinkedin}
                setContactLinkedin={setContactLinkedin}
                contactPhone={contactPhone}
                setContactPhone={setContactPhone}
                pagePolicy={pagePolicy}
                setPagePolicy={setPagePolicy}
                loading={loading}
                progressMessage={progressMessage}
                error={error}
                canSubmit={canSubmit}
                onSubmit={onSubmit}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {(result.pdf_page_count != null ||
              result.one_page_enforced ||
              result.page_policy_applied === "allow_multi") && (
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {result.page_policy_applied === "allow_multi" && (
                  <span className="rounded-full border border-sky-800/50 bg-sky-950/40 px-3 py-1 text-sky-200/90">
                    여러 페이지 허용 모드
                  </span>
                )}
                {result.pdf_page_count != null && (
                  <span className="rounded-full border border-zinc-700 bg-zinc-900/80 px-3 py-1 text-zinc-300">
                    Server PDF:{" "}
                    <strong className="text-zinc-100">
                      {result.pdf_page_count} page{result.pdf_page_count === 1 ? "" : "s"}
                    </strong>
                  </span>
                )}
                {result.one_page_enforced && (
                  <span className="rounded-full border border-emerald-800/60 bg-emerald-950/40 px-3 py-1 text-emerald-300/95">
                    Tightened to 1 page (auto revision)
                  </span>
                )}
                {result.pdf_page_count != null && result.pdf_page_count > 1 && (
                  <span className="rounded-full border border-amber-800/50 bg-amber-950/30 px-3 py-1 text-amber-200/90">
                    Still multi-page after max revisions — trim manually or shorten source
                  </span>
                )}
              </div>
            )}
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
                onClick={() => downloadTex(result.latex_document)}
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
              <button
                type="button"
                onClick={() => downloadCoachingMd(result)}
                className="rounded-lg border border-emerald-700 px-3 py-1.5 text-sm text-emerald-400 hover:bg-emerald-950/50"
              >
                Download coaching (.md)
              </button>
            </div>

            <div className="flex gap-1 rounded-lg bg-zinc-900 p-1">
              {(["preview", "coaching", "latex"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTab(t)}
                  className={`flex-1 rounded-md py-2 text-sm font-medium capitalize transition ${
                    tab === t ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {t === "latex" ? "LaTeX" : t}
                </button>
              ))}
            </div>

            {tab === "preview" && (
              <PdfPreview
                result={result}
                pdfUrl={pdfUrl}
                pdfBlob={pdfBlob}
                pdfLoading={pdfLoading}
                pdfError={pdfError}
                showTextPreview={showTextPreview}
                setShowTextPreview={setShowTextPreview}
                onRebuild={() => setPdfRefresh((n) => n + 1)}
              />
            )}

            {tab === "coaching" && <CoachingPanel result={result} />}

            {tab === "latex" && <LatexViewer latex={result.latex_document} />}
          </div>
        )}
      </main>
    </div>
  );
}
