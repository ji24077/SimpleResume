"use client";

import { useRef, useEffect, useCallback } from "react";
import type {
  ResumeSectionView,
  ResumeRoleView,
  ResumeBulletView,
  ReviewIssue,
  IssueSeverity,
} from "@/lib/types";

const SEV_HIGHLIGHT: Record<IssueSeverity, { bg: string; border: string; hover: string }> = {
  critical: {
    bg: "bg-red-500/10",
    border: "border-l-red-500",
    hover: "hover:bg-red-500/20",
  },
  moderate: {
    bg: "bg-amber-500/10",
    border: "border-l-amber-500",
    hover: "hover:bg-amber-500/20",
  },
  minor: {
    bg: "bg-sky-500/8",
    border: "border-l-sky-500",
    hover: "hover:bg-sky-500/15",
  },
};

function worstSeverity(issueIds: string[], issueMap: Map<string, ReviewIssue>): IssueSeverity | null {
  let worst: IssueSeverity | null = null;
  const order: IssueSeverity[] = ["critical", "moderate", "minor"];
  for (const id of issueIds) {
    const issue = issueMap.get(id);
    if (!issue) continue;
    const sev = issue.severity as IssueSeverity;
    if (!worst || order.indexOf(sev) < order.indexOf(worst)) worst = sev;
  }
  return worst;
}

function issueCountBadge(count: number, severity: IssueSeverity) {
  const colors: Record<IssueSeverity, string> = {
    critical: "bg-red-600 text-white",
    moderate: "bg-amber-600 text-white",
    minor: "bg-sky-600 text-white",
  };
  return (
    <span className={`inline-flex items-center justify-center rounded-full px-1.5 py-0.5 text-[9px] font-bold leading-none ${colors[severity]}`}>
      {count}
    </span>
  );
}

interface AnnotatedBulletProps {
  bullet: ResumeBulletView;
  issueMap: Map<string, ReviewIssue>;
  selectedIssueId: string | null;
  onClickIssue: (issue: ReviewIssue) => void;
}

function AnnotatedBullet({ bullet, issueMap, selectedIssueId, onClickIssue }: AnnotatedBulletProps) {
  const hasIssues = bullet.issue_ids.length > 0;
  const sev = worstSeverity(bullet.issue_ids, issueMap);
  const isSelected = bullet.issue_ids.includes(selectedIssueId || "");
  const style = sev ? SEV_HIGHLIGHT[sev] : null;

  const relatedIssues = bullet.issue_ids.map((id) => issueMap.get(id)).filter(Boolean) as ReviewIssue[];

  const handleClick = () => {
    if (relatedIssues.length > 0) {
      onClickIssue(relatedIssues[0]);
    }
  };

  return (
    <li
      data-bullet-id={bullet.id}
      className={`relative rounded-md px-3 py-1.5 text-sm leading-relaxed transition-all ${
        hasIssues
          ? `cursor-pointer border-l-2 ${style?.bg} ${style?.border} ${style?.hover} ${
              isSelected ? "ring-2 ring-sky-500/40 !bg-sky-500/15" : ""
            }`
          : "border-l-2 border-l-transparent text-zinc-300"
      }`}
      onClick={hasIssues ? handleClick : undefined}
      role={hasIssues ? "button" : undefined}
      tabIndex={hasIssues ? 0 : undefined}
      onKeyDown={hasIssues ? (e) => { if (e.key === "Enter" || e.key === " ") handleClick(); } : undefined}
      aria-label={hasIssues ? `${relatedIssues.length} issue(s): ${relatedIssues[0]?.title}. Click to see fix.` : undefined}
    >
      <span className={hasIssues ? "text-zinc-200" : "text-zinc-400"}>{bullet.text}</span>
      {hasIssues && sev && (
        <span className="ml-2 inline-flex items-center gap-1">
          {issueCountBadge(relatedIssues.length, sev)}
          <span className="text-[10px] text-zinc-500">{relatedIssues[0]?.title}</span>
        </span>
      )}
    </li>
  );
}

interface AnnotatedRoleProps {
  role: ResumeRoleView;
  issueMap: Map<string, ReviewIssue>;
  selectedIssueId: string | null;
  onClickIssue: (issue: ReviewIssue) => void;
}

function AnnotatedRole({ role, issueMap, selectedIssueId, onClickIssue }: AnnotatedRoleProps) {
  return (
    <div className="mb-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-sm font-semibold text-zinc-100">{role.company}</span>
        {role.title && <span className="text-sm text-zinc-400">{role.title}</span>}
        {role.date_range && <span className="text-xs text-zinc-600">{role.date_range}</span>}
      </div>
      {role.bullets.length > 0 && (
        <ul className="mt-2 space-y-1.5 pl-1">
          {role.bullets.map((bullet) => (
            <AnnotatedBullet
              key={bullet.id}
              bullet={bullet}
              issueMap={issueMap}
              selectedIssueId={selectedIssueId}
              onClickIssue={onClickIssue}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

interface AnnotatedResumeProps {
  sections: ResumeSectionView[];
  issues: ReviewIssue[];
  selectedIssueId: string | null;
  onClickIssue: (issue: ReviewIssue) => void;
  pdfUrl: string | null;
}

export default function AnnotatedResume({
  sections,
  issues,
  selectedIssueId,
  onClickIssue,
  pdfUrl,
}: AnnotatedResumeProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const issueMap = new Map(issues.map((i) => [i.id, i]));

  const scrollToSelectedBullet = useCallback(() => {
    if (!selectedIssueId || !containerRef.current) return;
    const issue = issueMap.get(selectedIssueId);
    if (!issue) return;
    const bulletId = issue.location.bullet_id;
    if (bulletId) {
      const el = containerRef.current.querySelector(`[data-bullet-id="${bulletId}"]`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
    }
    const sectionId = issue.location.section_id;
    if (sectionId) {
      const el = containerRef.current.querySelector(`[data-section-id="${sectionId}"]`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIssueId]);

  useEffect(() => {
    scrollToSelectedBullet();
  }, [scrollToSelectedBullet]);

  const hasSections = sections.length > 0;

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
      {/* Tab: Annotated view vs PDF */}
      <div className="flex shrink-0 items-center gap-2 border-b border-zinc-800 px-4 py-2">
        <span className="text-xs font-semibold text-zinc-300">
          {hasSections ? "Annotated Resume" : "Resume Preview"}
        </span>
        {hasSections && (
          <span className="rounded-md bg-sky-900/40 px-1.5 py-0.5 text-[9px] font-medium text-sky-400">
            Click highlighted bullets to see fixes
          </span>
        )}
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto">
        {hasSections ? (
          <div className="mx-auto max-w-2xl space-y-6 px-6 py-6">
            {sections.map((section) => (
              <div key={section.id} data-section-id={section.id}>
                {section.type === "header" ? (
                  <div className="mb-4 border-b border-zinc-800 pb-4">
                    {section.lines.map((line, i) => (
                      <p key={i} className={i === 0 ? "text-lg font-bold text-white" : "text-sm text-zinc-400"}>
                        {line}
                      </p>
                    ))}
                  </div>
                ) : (
                  <>
                    <h3 className="mb-2 text-xs font-bold uppercase tracking-widest text-sky-500/80">
                      {section.title}
                    </h3>

                    {section.type === "experience" && section.roles.length > 0 ? (
                      section.roles.map((role) => (
                        <AnnotatedRole
                          key={role.id}
                          role={role}
                          issueMap={issueMap}
                          selectedIssueId={selectedIssueId}
                          onClickIssue={onClickIssue}
                        />
                      ))
                    ) : section.type === "skills" ? (
                      <div className="flex flex-wrap gap-1.5">
                        {section.lines.map((skill, i) => (
                          <span
                            key={i}
                            className="rounded-md border border-zinc-800 bg-zinc-900/60 px-2 py-1 text-xs text-zinc-300"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-1">
                        {section.lines.map((line, i) => (
                          <p key={i} className="text-sm leading-relaxed text-zinc-400">
                            {line}
                          </p>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        ) : pdfUrl ? (
          <iframe
            title="Resume PDF Preview"
            src={`${pdfUrl}#toolbar=0&navpanes=0`}
            className="h-full w-full"
            style={{ minHeight: "700px" }}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-8">
            <p className="text-sm text-zinc-500">No resume preview available.</p>
          </div>
        )}
      </div>
    </div>
  );
}
