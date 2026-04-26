import type { GenerateResponse } from "@/lib/types";

const KIND_LABEL: Record<string, string> = {
  education: "Education",
  experience: "Experience",
  project: "Project",
  skills: "Skills",
  summary: "Summary",
};

interface PdfPreviewProps {
  result: GenerateResponse;
  pdfUrl: string | null;
  pdfBlob: Blob | null;
  pdfLoading: boolean;
  pdfError: string | null;
  showTextPreview: boolean;
  setShowTextPreview: (v: boolean) => void;
  onRebuild: () => void;
}

export default function PdfPreview({
  result,
  pdfUrl,
  pdfLoading,
  pdfError,
  showTextPreview,
  setShowTextPreview,
  onRebuild,
}: PdfPreviewProps) {
  return (
    <div className="space-y-4 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-zinc-300">PDF preview (Docker TeX Live + latexmk)</p>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onRebuild}
            disabled={pdfLoading}
            className="text-xs text-amber-400 hover:underline disabled:opacity-40"
          >
            Rebuild PDF
          </button>
          <button
            type="button"
            onClick={() => setShowTextPreview(!showTextPreview)}
            className="text-xs text-emerald-400 hover:underline"
          >
            {showTextPreview ? "Hide text list" : "Show plain text list"}
          </button>
        </div>
      </div>
      {pdfLoading && (
        <p className="text-sm text-zinc-500">Compiling PDF… (first run may take 10–30s)</p>
      )}
      {pdfError && (
        <div className="rounded-lg border border-amber-900/50 bg-amber-950/30 p-4 text-sm text-amber-100">
          <p className="font-medium text-amber-200">PDF preview unavailable</p>
          <p className="mt-2 whitespace-pre-wrap font-mono text-xs text-zinc-400">{pdfError.slice(0, 2000)}</p>
          <p className="mt-3 text-xs text-zinc-500">
            Ensure Docker is running and the TeX image is built:{" "}
            <code className="rounded bg-zinc-800 px-1">docker compose build texlive</code> from the repo root,
            then restart the API. See README for <code className="rounded bg-zinc-800 px-1">LATEX_DOCKER_*</code>{" "}
            in <code className="rounded bg-zinc-800 px-1">api/.env</code>.
          </p>
        </div>
      )}
      {pdfUrl && !pdfLoading && (
        <div className="overflow-hidden rounded-lg border border-zinc-700 bg-white">
          <iframe
            title="Resume PDF"
            src={`${pdfUrl}#toolbar=1`}
            className="h-[min(85vh,1100px)] w-full"
          />
        </div>
      )}
      {showTextPreview && (
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
    </div>
  );
}
