"use client";

import { ExperienceEntry } from "@/lib/types";
import BulletList from "./BulletList";
import EntryCard from "./EntryCard";

type ExperienceSectionProps = {
  experience: ExperienceEntry[];
  onChange: (next: ExperienceEntry[]) => void;
};

const FIELD_BASE =
  "w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600";

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
              <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
                Title
              </span>
              <input
                type="text"
                value={entry.title}
                onChange={(e) => update(i, { title: e.target.value })}
                placeholder="Software Engineer Intern"
                className={FIELD_BASE}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
                Company
              </span>
              <input
                type="text"
                value={entry.company}
                onChange={(e) => update(i, { company: e.target.value })}
                placeholder="NVIDIA"
                className={FIELD_BASE}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
                Dates
              </span>
              <input
                type="text"
                value={entry.date}
                onChange={(e) => update(i, { date: e.target.value })}
                placeholder="May 2024 — Aug 2024"
                className={FIELD_BASE}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
                Location
              </span>
              <input
                type="text"
                value={entry.location}
                onChange={(e) => update(i, { location: e.target.value })}
                placeholder="Santa Clara, CA"
                className={FIELD_BASE}
              />
            </label>
          </div>
          <div>
            <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
              Bullets
            </span>
            <BulletList
              bullets={entry.bullets}
              onChange={(next) => update(i, { bullets: next })}
              minBullets={1}
            />
          </div>
        </EntryCard>
      ))}
      <button
        type="button"
        onClick={add}
        className="w-full rounded-xl border border-dashed border-zinc-700 px-4 py-3 text-sm text-zinc-300 hover:border-emerald-700 hover:text-emerald-300"
      >
        + Add experience entry
      </button>
    </div>
  );
}
