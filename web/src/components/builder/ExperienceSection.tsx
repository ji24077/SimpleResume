"use client";

import { ExperienceEntry } from "@/lib/types";
import BulletList from "./BulletList";
import EntryCard from "./EntryCard";

type ExperienceSectionProps = {
  experience: ExperienceEntry[];
  onChange: (next: ExperienceEntry[]) => void;
};

const EMPTY_EXP: ExperienceEntry = {
  title: "",
  company: "",
  date: "",
  location: "",
  bullets: [""],
};

export default function ExperienceSection({ experience, onChange }: ExperienceSectionProps) {
  const update = (i: number, patch: Partial<ExperienceEntry>) => {
    onChange(experience.map((e, idx) => (idx === i ? { ...e, ...patch } : e)));
  };
  const remove = (i: number) => {
    onChange(experience.filter((_, idx) => idx !== i));
  };
  const add = () => {
    onChange([...experience, { ...EMPTY_EXP, bullets: [""] }]);
  };

  return (
    <div className="space-y-3">
      {experience.map((entry, i) => (
        <EntryCard
          key={i}
          heading={entry.title}
          subheading={[entry.company, entry.date].filter(Boolean).join(" · ")}
          onDelete={() => remove(i)}
          deleteLabel={`Remove experience entry ${i + 1}`}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="t-label mb-1 block">Title</span>
              <input
                type="text"
                value={entry.title}
                onChange={(e) => update(i, { title: e.target.value })}
                placeholder="Software Engineer Intern"
                className="input"
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Company</span>
              <input
                type="text"
                value={entry.company}
                onChange={(e) => update(i, { company: e.target.value })}
                placeholder="NVIDIA"
                className="input"
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Dates</span>
              <input
                type="text"
                value={entry.date}
                onChange={(e) => update(i, { date: e.target.value })}
                placeholder="May 2024 — Aug 2024"
                className="input"
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Location</span>
              <input
                type="text"
                value={entry.location}
                onChange={(e) => update(i, { location: e.target.value })}
                placeholder="Santa Clara, CA"
                className="input"
              />
            </label>
          </div>
          <div>
            <span className="t-label mb-1 block">Bullets</span>
            <BulletList
              bullets={entry.bullets}
              onChange={(next) => update(i, { bullets: next })}
              minBullets={1}
            />
          </div>
        </EntryCard>
      ))}
      <button type="button" onClick={add} className="btn btn-soft" style={{ width: "100%" }}>
        + Add experience entry
      </button>
    </div>
  );
}
