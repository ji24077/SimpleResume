"use client";

import { ResumeData } from "@/lib/types";
import EducationSection from "./EducationSection";
import ExperienceSection from "./ExperienceSection";
import HeaderSection from "./HeaderSection";
import ProjectsSection from "./ProjectsSection";
import SectionAccordion from "./SectionAccordion";
import SkillsSection from "./SkillsSection";

type ResumeFormProps = {
  value: ResumeData;
  onChange: (next: ResumeData) => void;
  onSubmit: () => void;
  onBack?: () => void;
  warnings?: string[];
  submitting?: boolean;
};

export default function ResumeForm({
  value,
  onChange,
  onSubmit,
  onBack,
  warnings = [],
  submitting = false,
}: ResumeFormProps) {
  const skillsCount =
    value.skills.languages.length + value.skills.frameworks.length + value.skills.tools.length;

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-4 py-6">
      <header className="space-y-2">
        <h2 className="text-xl font-semibold text-zinc-100">Review what we read</h2>
        <p className="text-sm text-zinc-400">
          Fix anything that looks off, then generate. You can also skip straight to generation if
          everything looks right.
        </p>
      </header>

      {warnings.length > 0 && (
        <div className="rounded-xl border border-amber-700/60 bg-amber-950/40 px-4 py-3 text-sm text-amber-200">
          <p className="mb-1 font-medium">Parser notes</p>
          <ul className="list-disc space-y-0.5 pl-5">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-3">
        <SectionAccordion title="Contact">
          <HeaderSection
            header={value.header}
            onChange={(header) => onChange({ ...value, header })}
          />
        </SectionAccordion>

        <SectionAccordion title="Education" count={value.education.length}>
          <EducationSection
            education={value.education}
            onChange={(education) => onChange({ ...value, education })}
          />
        </SectionAccordion>

        <SectionAccordion title="Experience" count={value.experience.length}>
          <ExperienceSection
            experience={value.experience}
            onChange={(experience) => onChange({ ...value, experience })}
          />
        </SectionAccordion>

        <SectionAccordion title="Projects" count={value.projects.length}>
          <ProjectsSection
            projects={value.projects}
            onChange={(projects) => onChange({ ...value, projects })}
          />
        </SectionAccordion>

        <SectionAccordion title="Skills" count={skillsCount}>
          <SkillsSection
            skills={value.skills}
            onChange={(skills) => onChange({ ...value, skills })}
          />
        </SectionAccordion>
      </div>

      <div className="sticky bottom-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/90 px-4 py-3 backdrop-blur">
        {onBack ? (
          <button
            type="button"
            onClick={onBack}
            disabled={submitting}
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:border-zinc-500 hover:text-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Back to upload
          </button>
        ) : (
          <span />
        )}
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Generating…" : "Looks good — Generate"}
        </button>
      </div>
    </div>
  );
}
