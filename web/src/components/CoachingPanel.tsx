import type { GenerateResponse } from "@/lib/types";

const KIND_LABEL: Record<string, string> = {
  education: "Education",
  experience: "Experience",
  project: "Project",
  skills: "Skills",
  summary: "Summary",
};

interface CoachingPanelProps {
  result: GenerateResponse;
}

export default function CoachingPanel({ result }: CoachingPanelProps) {
  return (
    <div className="space-y-8 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
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
    </div>
  );
}
