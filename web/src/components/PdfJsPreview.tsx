"use client";

import { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

type Props = { fileUrl: string };

/**
 * PDF.js via react-pdf (same rendering stack many browsers use for PDF).
 */
export default function PdfJsPreview({ fileUrl }: Props) {
  const [numPages, setNumPages] = useState(0);
  const [width, setWidth] = useState(800);

  useEffect(() => {
    pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
    const measure = () =>
      setWidth(Math.min(840, Math.max(280, typeof window !== "undefined" ? window.innerWidth - 48 : 800)));
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  return (
    <div className="rounded-lg bg-zinc-100 p-2">
      <Document
        file={fileUrl}
        onLoadSuccess={({ numPages: n }) => setNumPages(n)}
        loading={<p className="py-8 text-center text-sm text-zinc-600">Rendering PDF…</p>}
        error={
          <p className="py-8 text-center text-sm text-red-800">
            Could not render PDF in the viewer. Use <strong>Download PDF</strong> or open the blob URL in a new tab.
          </p>
        }
        className="flex flex-col items-center gap-2"
      >
        {Array.from({ length: numPages }, (_, i) => (
          <Page
            key={i + 1}
            pageNumber={i + 1}
            width={width}
            className="shadow"
            renderTextLayer
            renderAnnotationLayer
          />
        ))}
      </Document>
    </div>
  );
}
