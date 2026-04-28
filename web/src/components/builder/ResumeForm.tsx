"use client";

import { ResumeData } from "@/lib/types";
import EducationSection from "./EducationSection";
import ExperienceSection from "./ExperienceSection";
import HeaderSection from "./HeaderSection";
import ProjectsSection from "./ProjectsSection";
import PublicationsSection from "./PublicationsSection";
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
    <div className="space-y-5">
      <header>
        <div className="t-eyebrow" style={{ marginBottom: 6 }}>
          verify · what we read
        </div>
        <h2 className="font-display" style={{ fontSize: 28, fontWeight: 600 }}>
          Review the parse before we rewrite
        </h2>
        <p style={{ fontSize: 14, color: "var(--fg-3)", marginTop: 6, maxWidth: 640 }}>
          Fix anything that looks off, then generate. Anything you change here flows into the rewrite —
          we never invent details that aren&apos;t in the source.
        </p>
      </header>

      {warnings.length > 0 && (
        <div
          className="card"
          style={{
            background: "var(--warn-bg)",
            borderColor: "transparent",
            borderLeft: "3px solid var(--warn)",
            color: "var(--warn)",
          }}
        >
          <p style={{ marginBottom: 6, fontWeight: 600 }}>Parser notes</p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
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

        <SectionAccordion title="Publications" count={value.publications.length}>
          <PublicationsSection
            publications={value.publications}
            onChange={(publications) => onChange({ ...value, publications })}
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

      <div
        className="row between"
        style={{
          position: "sticky",
          bottom: 16,
          background: "color-mix(in oklab, var(--canvas) 92%, transparent)",
          backdropFilter: "blur(10px)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: "12px 16px",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        {onBack ? (
          <button type="button" onClick={onBack} disabled={submitting} className="btn btn-soft btn-sm">
            ← Back to upload
          </button>
        ) : (
          <span />
        )}
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          className="btn btn-primary"
          style={{ padding: "10px 22px" }}
        >
          {submitting ? "Generating…" : "Looks good — generate →"}
        </button>
      </div>
    </div>
  );
}
