"use client";

import { EducationEntry } from "@/lib/types";
import BulletList from "./BulletList";
import EntryCard from "./EntryCard";

type EducationSectionProps = {
  education: EducationEntry[];
  onChange: (next: EducationEntry[]) => void;
};

const FIELD_BASE = "input";

const EMPTY_EDU: EducationEntry = {
  school: "",
  degree: "",
  date: "",
  location: "",
  bullets: [],
};

export default function EducationSection({ education, onChange }: EducationSectionProps) {
  const update = (i: number, patch: Partial<EducationEntry>) => {
    onChange(education.map((e, idx) => (idx === i ? { ...e, ...patch } : e)));
  };
  const remove = (i: number) => {
    onChange(education.filter((_, idx) => idx !== i));
  };
  const add = () => {
    onChange([...education, { ...EMPTY_EDU, bullets: [] }]);
  };

  return (
    <div className="space-y-3">
      {education.map((entry, i) => (
        <EntryCard
          key={i}
          heading={entry.school}
          subheading={entry.degree}
          onDelete={() => remove(i)}
          deleteLabel={`Remove education entry ${i + 1}`}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="t-label mb-1 block">School</span>
              <input
                type="text"
                value={entry.school}
                onChange={(e) => update(i, { school: e.target.value })}
                placeholder="University of…"
                className={FIELD_BASE}
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Degree</span>
              <input
                type="text"
                value={entry.degree}
                onChange={(e) => update(i, { degree: e.target.value })}
                placeholder="B.S. Computer Science"
                className={FIELD_BASE}
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Dates</span>
              <input
                type="text"
                value={entry.date}
                onChange={(e) => update(i, { date: e.target.value })}
                placeholder="Aug 2021 — May 2025"
                className={FIELD_BASE}
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Location</span>
              <input
                type="text"
                value={entry.location}
                onChange={(e) => update(i, { location: e.target.value })}
                placeholder="City, State"
                className={FIELD_BASE}
              />
            </label>
          </div>
          <div>
            <span className="t-label mb-1 block">Highlights (optional)</span>
            <BulletList
              bullets={entry.bullets}
              onChange={(next) => update(i, { bullets: next })}
              placeholder="GPA, honors, relevant coursework…"
            />
          </div>
        </EntryCard>
      ))}
      <button type="button" onClick={add} className="btn btn-soft" style={{ width: "100%" }}>
        + Add education entry
      </button>
    </div>
  );
}
