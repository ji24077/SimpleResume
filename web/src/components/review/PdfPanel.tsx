"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { ReviewIssue } from "@/lib/types";
import { downloadPdfBlob, downloadTex } from "@/lib/upload";

const PdfAnnotationViewer = dynamic(() => import("./PdfAnnotationViewer"), {
  ssr: false,
  loading: () => (
    <div
      className="card"
      style={{ height: "100%", display: "grid", placeItems: "center", background: "var(--canvas-alt)" }}
    >
      <span className="font-mono muted" style={{ fontSize: 12 }}>Loading viewer…</span>
    </div>
  ),
});

type Props = {
  pdfUrl: string | null;
  pdfBlob: Blob | null;
  pdfStatus: "idle" | "loading" | "ready" | "error";
  pdfError: string | null;
  latex: string;
  issues: ReviewIssue[];
  selectedId: string | null;
  onSelectIssue: (id: string | null) => void;
};

export default function PdfPanel({
  pdfUrl,
  pdfBlob,
  pdfStatus,
  pdfError,
  latex,
  issues,
  selectedId,
  onSelectIssue,
}: Props) {
  const [zoom, setZoom] = useState(92);

  return (
    <div className="card" style={{ padding: 18 }}>
      <div className="row between" style={{ marginBottom: 12 }}>
        <div className="t-label">Annotated PDF</div>
        <div className="row" style={{ gap: 6 }}>
          <button
            type="button"
            className="btn btn-soft btn-sm"
            style={{ padding: "4px 8px" }}
            onClick={() => setZoom((z) => Math.max(60, z - 8))}
          >
            −
          </button>
          <span className="font-mono muted" style={{ fontSize: 11 }}>
            {zoom}%
          </span>
          <button
            type="button"
            className="btn btn-soft btn-sm"
            style={{ padding: "4px 8px" }}
            onClick={() => setZoom((z) => Math.min(160, z + 8))}
          >
            +
          </button>
          <span style={{ width: 1, height: 18, background: "var(--border)", margin: "0 4px" }} />
          <button
            type="button"
            className="btn btn-soft btn-sm"
            disabled={!pdfBlob}
            onClick={() => pdfBlob && downloadPdfBlob(pdfBlob)}
          >
            Download .pdf
          </button>
          <button
            type="button"
            className="btn btn-soft btn-sm"
            disabled={!latex}
            onClick={() => latex && downloadTex(latex)}
          >
            Download .tex
          </button>
        </div>
      </div>

      <div style={{ height: 720, transform: `scale(${zoom / 100})`, transformOrigin: "top left", width: `${10000 / zoom}%` }}>
        {pdfStatus === "loading" && (
          <div
            className="card"
            style={{
              height: "100%",
              display: "grid",
              placeItems: "center",
              background: "var(--canvas-alt)",
            }}
          >
            <div className="row" style={{ gap: 10 }}>
              <div
                className="h-5 w-5 animate-spin rounded-full"
                style={{
                  width: 18,
                  height: 18,
                  border: "2px solid var(--accent)",
                  borderTopColor: "transparent",
                  borderRadius: "50%",
                }}
              />
              <span className="font-mono muted" style={{ fontSize: 12 }}>
                Compiling PDF…
              </span>
            </div>
          </div>
        )}
        {pdfStatus === "error" && (
          <div
            className="card"
            style={{
              padding: 18,
              background: "var(--error-bg)",
              borderColor: "transparent",
              borderLeft: "3px solid var(--error)",
              color: "var(--error)",
            }}
          >
            {pdfError ?? "PDF compile failed."}
          </div>
        )}
        {pdfStatus === "ready" && pdfUrl && (
          <PdfAnnotationViewer
            pdfUrl={pdfUrl}
            issues={issues}
            selectedIssueId={selectedId}
            onSelectIssue={(iss) => onSelectIssue(iss.id)}
          />
        )}
      </div>

      <div className="row between" style={{ marginTop: 12 }}>
        <div className="font-mono muted" style={{ fontSize: 11 }}>
          Letter · 8.5 × 11
        </div>
        <div className="font-mono muted" style={{ fontSize: 11 }}>
          {pdfStatus === "ready" ? "compiled" : pdfStatus === "loading" ? "compiling…" : ""}
        </div>
      </div>
    </div>
  );
}
