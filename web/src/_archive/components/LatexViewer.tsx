interface LatexViewerProps {
  latex: string;
}

export default function LatexViewer({ latex }: LatexViewerProps) {
  return (
    <pre className="max-h-[70vh] overflow-auto rounded-2xl border border-zinc-800 bg-zinc-950 p-4 text-xs leading-relaxed text-emerald-200/80">
      {latex}
    </pre>
  );
}
