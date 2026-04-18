"use client";

function scoreColor(score: number): string {
  if (score >= 9) return "text-emerald-400 border-emerald-400/30 bg-emerald-950/40";
  if (score >= 8) return "text-emerald-500 border-emerald-500/30 bg-emerald-950/30";
  if (score >= 7) return "text-sky-400 border-sky-400/30 bg-sky-950/40";
  if (score >= 6) return "text-amber-400 border-amber-400/30 bg-amber-950/40";
  return "text-red-400 border-red-400/30 bg-red-950/40";
}

const SIZE_CLASSES = {
  sm: "h-7 min-w-7 px-1.5 text-xs",
  md: "h-9 min-w-9 px-2 text-sm",
  lg: "h-14 min-w-14 px-3 text-2xl",
} as const;

export default function ScoreBadge({
  score,
  size = "md",
}: {
  score: number;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <span
      className={`inline-flex items-center justify-center rounded-full border font-bold tabular-nums ${scoreColor(score)} ${SIZE_CLASSES[size]}`}
    >
      {score.toFixed(1)}
    </span>
  );
}
