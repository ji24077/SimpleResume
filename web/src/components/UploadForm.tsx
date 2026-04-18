import type { PagePolicy } from "@/lib/types";

interface UploadFormProps {
  file: File | null;
  setFile: (f: File | null) => void;
  paste: string;
  setPaste: (s: string) => void;
  contactEmail: string;
  setContactEmail: (s: string) => void;
  contactLinkedin: string;
  setContactLinkedin: (s: string) => void;
  contactPhone: string;
  setContactPhone: (s: string) => void;
  pagePolicy: PagePolicy;
  setPagePolicy: (p: PagePolicy) => void;
  loading: boolean;
  progressMessage: string | null;
  error: string | null;
  canSubmit: boolean;
  onSubmit: () => void;
}

export default function UploadForm({
  file,
  setFile,
  paste,
  setPaste,
  contactEmail,
  setContactEmail,
  contactLinkedin,
  setContactLinkedin,
  contactPhone,
  setContactPhone,
  pagePolicy,
  setPagePolicy,
  loading,
  progressMessage,
  error,
  canSubmit,
  onSubmit,
}: UploadFormProps) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-8">
      <h2 className="mb-2 text-sm font-medium text-zinc-300">1. Upload or paste your draft</h2>
      <p className="mb-6 text-sm text-zinc-500">
        PDF, .tex, or plain text. We extract content and regenerate an ATS-friendly, high-impact layout in
        LaTeX — ready to preview and download.
      </p>
      <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-zinc-700 bg-zinc-900 px-6 py-12 transition hover:border-emerald-600/50 hover:bg-zinc-800/50">
        <input
          type="file"
          accept=".pdf,.tex,.txt"
          className="hidden"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
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
        }}
        placeholder="Paste resume text here…"
        rows={10}
        className="mt-4 w-full resize-y rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
      />
      <div className="mt-6 space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/50 px-4 py-4">
        <p className="text-xs font-medium text-zinc-400">연락처 (붙여넣기 시 권장)</p>
        <p className="text-xs text-zinc-500">
          원문에 이메일·LinkedIn이 분명하지 않으면 생성 전에 입력을 요청합니다. 파일 업로드(PDF 등)일 때는
          검사를 건너뜁니다.
        </p>
        <input
          type="email"
          autoComplete="email"
          placeholder="이메일 (예: you@school.edu)"
          value={contactEmail}
          onChange={(e) => setContactEmail(e.target.value)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
        />
        <input
          type="url"
          autoComplete="url"
          placeholder="LinkedIn (https://linkedin.com/in/…)"
          value={contactLinkedin}
          onChange={(e) => setContactLinkedin(e.target.value)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
        />
        <input
          type="tel"
          autoComplete="tel"
          placeholder="전화 (선택)"
          value={contactPhone}
          onChange={(e) => setContactPhone(e.target.value)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
        />
      </div>
      <div className="mt-6 space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/50 px-4 py-4">
        <p className="text-xs font-medium text-zinc-400">페이지 정책</p>
        <label className="flex cursor-pointer items-start gap-3 text-sm text-zinc-300">
          <input
            type="radio"
            name="pagePolicy"
            checked={pagePolicy === "strict_one_page"}
            onChange={() => setPagePolicy("strict_one_page")}
            className="mt-1 accent-emerald-500"
          />
          <span>
            <strong className="text-zinc-100">1페이지 고정</strong>
            <span className="mt-0.5 block text-xs text-zinc-500">
              2페이지 이상이면 서버가 1페이지에 맞게 다시 줄입니다. 진행 메시지가 버튼 위에 표시됩니다.
            </span>
          </span>
        </label>
        <label className="flex cursor-pointer items-start gap-3 text-sm text-zinc-300">
          <input
            type="radio"
            name="pagePolicy"
            checked={pagePolicy === "allow_multi"}
            onChange={() => setPagePolicy("allow_multi")}
            className="mt-1 accent-emerald-500"
          />
          <span>
            <strong className="text-zinc-100">여러 페이지 허용</strong>
            <span className="mt-0.5 block text-xs text-zinc-500">
              1페이지 강제 없이 생성만 합니다. 긴 이력서에 적합합니다.
            </span>
          </span>
        </label>
      </div>
      {loading && progressMessage && (
        <p className="mt-4 rounded-lg border border-emerald-900/40 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-200/95">
          {progressMessage}
        </p>
      )}
      {error && (
        <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-sm text-red-300">{error}</p>
      )}
      <button
        type="button"
        disabled={!canSubmit || loading}
        onClick={onSubmit}
        className="mt-6 w-full rounded-xl bg-emerald-600 py-3 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading
          ? progressMessage ?? "생성 중… (30–120초 정도 걸릴 수 있습니다)"
          : "Generate resume"}
      </button>
    </div>
  );
}
