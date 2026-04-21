"use client";

import { ProjectEntry } from "@/lib/types";
import BulletList from "./BulletList";
import EntryCard from "./EntryCard";

type ProjectsSectionProps = {
  projects: ProjectEntry[];
  onChange: (next: ProjectEntry[]) => void;
};

const FIELD_BASE =
  "w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600";

const EMPTY_PROJECT: ProjectEntry = {
  name: "",
  date: "",
  tech_line: "",
  bullets: [],
};

export default function ProjectsSection({ projects, onChange }: ProjectsSectionProps) {
  const update = (i: number, patch: Partial<ProjectEntry>) => {
    onChange(projects.map((p, idx) => (idx === i ? { ...p, ...patch } : p)));
  };
  const remove = (i: number) => {
    onChange(projects.filter((_, idx) => idx !== i));
  };
  const add = () => {
    onChange([...projects, { ...EMPTY_PROJECT, bullets: [] }]);
  };

  return (
    <div className="space-y-3">
      {projects.map((entry, i) => (
        <EntryCard
          key={i}
          heading={entry.name}
          subheading={entry.tech_line}
          onDelete={() => remove(i)}
          deleteLabel={`Remove project entry ${i + 1}`}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
                Project name
              </span>
              <input
                type="text"
                value={entry.name}
                onChange={(e) => update(i, { name: e.target.value })}
                placeholder="SimpleResume"
                className={FIELD_BASE}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
                Date
              </span>
              <input
                type="text"
                value={entry.date}
                onChange={(e) => update(i, { date: e.target.value })}
                placeholder="2025 — Present"
                className={FIELD_BASE}
              />
            </label>
          </div>
          <label className="block">
            <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
              Tech / tools
            </span>
            <input
              type="text"
              value={entry.tech_line}
              onChange={(e) => update(i, { tech_line: e.target.value })}
              placeholder="Python, FastAPI, Next.js"
              className={FIELD_BASE}
            />
          </label>
          <div>
            <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">
              Bullets
            </span>
            <BulletList
              bullets={entry.bullets}
              onChange={(next) => update(i, { bullets: next })}
            />
          </div>
        </EntryCard>
      ))}
      <button
        type="button"
        onClick={add}
        className="w-full rounded-xl border border-dashed border-zinc-700 px-4 py-3 text-sm text-zinc-300 hover:border-emerald-700 hover:text-emerald-300"
      >
        + Add project entry
      </button>
    </div>
  );
}
