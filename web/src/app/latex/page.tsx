"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

type CompilerHealth = {
  latex_docker_ready?: boolean;
  latex_docker_image?: string | null;
  latex_docker_only?: boolean;
  pdf_compile?: boolean;
  compile_hint?: string | null;
  docker?: boolean;
};

export default function LatexCompilePage() {
  const [tex, setTex] = useState("");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compiler, setCompiler] = useState<CompilerHealth | null>(null);
  const pdfUrlRef = useRef<string | null>(null);

  useEffect(() => {
    fetch("/api/backend-health")
      .then((r) => r.json())
      .then((d) => setCompiler((d.compiler as CompilerHealth) ?? null))
      .catch(() => setCompiler(null));
  }, []);

  useEffect(() => {
    return () => {
      if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current);
    };
  }, []);

  const compile = useCallback(async () => {
    const t = tex.trim();
    if (!t) {
      setError("LaTeX 소스를 입력하세요.");
      return;
    }
    if (!t.includes("\\documentclass")) {
      setError("전체 문서가 필요합니다: \\documentclass{...}부터 포함해야 합니다.");
      return;
    }
    setError(null);
    setLoading(true);
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
    }
    setPdfUrl(null);
    setPdfBlob(null);
    try {
      const res = await fetch("/api/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tex: t }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        setError(typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? {}, null, 2));
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfBlob(blob);
      setPdfUrl(url);
    } catch {
      setError("네트워크 오류 — API가 켜져 있는지 확인하세요.");
    } finally {
      setLoading(false);
    }
  }, [tex]);

  const downloadPdf = () => {
    if (!pdfBlob) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(pdfBlob);
    a.download = "compiled.pdf";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const downloadTex = () => {
    const blob = new Blob([tex], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "resume.tex";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div className="flex flex-wrap items-center gap-4">
            <Link href="/" className="text-lg font-semibold tracking-tight text-white hover:text-emerald-300">
              SimpleResume
            </Link>
            <span className="text-zinc-600">/</span>
            <h1 className="text-sm font-medium text-zinc-300">LaTeX → PDF (Docker TeX Live 권장)</h1>
          </div>
          <nav className="flex gap-3 text-sm">
            <Link href="/" className="text-zinc-400 hover:text-white">
              홈 (Generate)
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        {compiler && (
          <div
            className={`mb-6 rounded-xl border px-4 py-3 text-sm ${
              compiler.pdf_compile
                ? "border-emerald-900/50 bg-emerald-950/20 text-emerald-200/90"
                : "border-amber-900/50 bg-amber-950/30 text-amber-100"
            }`}
          >
            <p className="font-medium">
              컴파일 환경(기본 Overleaf급):{" "}
              {compiler.latex_docker_ready
                ? `Docker TeX Live + latexmk (${compiler.latex_docker_image ?? ""})`
                : compiler.latex_docker_image
                  ? "Docker 이미지가 설정됐는데 Docker를 쓸 수 없습니다. Docker Desktop을 켜고 이미지를 빌드하세요."
                  : "Docker 이미지가 비어 있어 호스트 TeX 폴백 모드입니다."}
            </p>
            {compiler.compile_hint && (
              <p className="mt-1 text-xs text-zinc-400">{compiler.compile_hint}</p>
            )}
            <p className="mt-2 text-xs text-zinc-500">
              기본값은 TinyTeX가 아니라{" "}
              <code className="rounded bg-zinc-800 px-1">docker compose build texlive</code> 로 만든{" "}
              <code className="rounded bg-zinc-800 px-1">simpleresume-texlive:full</code> 입니다. API 재시작 후{" "}
              <code className="rounded bg-zinc-800 px-1">/health</code>에서{" "}
              <code className="rounded bg-zinc-800 px-1">latex_docker_ready</code> 확인.
            </p>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="flex flex-col rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
            <label htmlFor="tex-src" className="mb-2 text-sm font-medium text-zinc-300">
              전체 .tex 붙여넣기
            </label>
            <textarea
              id="tex-src"
              spellCheck={false}
              value={tex}
              onChange={(e) => {
                setTex(e.target.value);
                setError(null);
              }}
              placeholder="% \\documentclass{article} ... 전체 소스"
              rows={22}
              className="min-h-[420px] w-full flex-1 resize-y rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
            />
            {error && (
              <pre className="mt-3 max-h-40 overflow-auto rounded-lg bg-red-950/40 p-3 text-xs text-red-200 whitespace-pre-wrap">
                {error}
              </pre>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={loading}
                onClick={compile}
                className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
              >
                {loading ? "컴파일 중…" : "Compile"}
              </button>
              <button
                type="button"
                onClick={downloadTex}
                disabled={!tex.trim()}
                className="rounded-xl border border-zinc-600 px-4 py-2.5 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-40"
              >
                .tex 저장
              </button>
              <button
                type="button"
                onClick={downloadPdf}
                disabled={!pdfBlob}
                className="rounded-xl border border-zinc-600 px-4 py-2.5 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-40"
              >
                PDF 저장
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
            <p className="mb-3 text-sm font-medium text-zinc-300">미리보기</p>
            {!pdfUrl && !loading && (
              <p className="py-16 text-center text-sm text-zinc-500">Compile을 누르면 여기에 PDF가 표시됩니다.</p>
            )}
            {loading && <p className="py-16 text-center text-sm text-zinc-400">PDF 빌드 중… (Docker는 첫 실행이 길 수 있음)</p>}
            {pdfUrl && !loading && (
              <div className="overflow-hidden rounded-lg border border-zinc-700 bg-white">
                <iframe title="Compiled PDF" src={`${pdfUrl}#toolbar=1`} className="h-[min(85vh,1100px)] w-full" />
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
