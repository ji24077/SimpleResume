"use client";

function tagColor(label: string): string {
  const l = label.toLowerCase();
  if (l.includes("strong")) return "border-emerald-700/50 bg-emerald-950/30 text-emerald-300";
  if (l.includes("missing") || l.includes("low impact"))
    return "border-amber-700/50 bg-amber-950/30 text-amber-300";
  if (l.includes("too long") || l.includes("generic"))
    return "border-zinc-600/50 bg-zinc-800/40 text-zinc-300";
  if (l.includes("recoverable"))
    return "border-sky-700/50 bg-sky-950/30 text-sky-300";
  return "border-zinc-700/50 bg-zinc-800/30 text-zinc-400";
}

export default function IssueTag({ label }: { label: string }) {
  return (
    <span
      className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${tagColor(label)}`}
    >
      {label}
    </span>
  );
}
