"use client";

import { ProjectEntry } from "@/lib/types";
import BulletList from "./BulletList";
import EntryCard from "./EntryCard";

type ProjectsSectionProps = {
  projects: ProjectEntry[];
  onChange: (next: ProjectEntry[]) => void;
};

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
              <span className="t-label mb-1 block">Project name</span>
              <input
                type="text"
                value={entry.name}
                onChange={(e) => update(i, { name: e.target.value })}
                placeholder="SimpleResume"
                className="input"
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Date</span>
              <input
                type="text"
                value={entry.date}
                onChange={(e) => update(i, { date: e.target.value })}
                placeholder="2025 — Present"
                className="input"
              />
            </label>
          </div>
          <label className="block">
            <span className="t-label mb-1 block">Tech / tools</span>
            <input
              type="text"
              value={entry.tech_line}
              onChange={(e) => update(i, { tech_line: e.target.value })}
              placeholder="Python, FastAPI, Next.js"
              className="input"
            />
          </label>
          <div>
            <span className="t-label mb-1 block">Bullets</span>
            <BulletList
              bullets={entry.bullets}
              onChange={(next) => update(i, { bullets: next })}
            />
          </div>
        </EntryCard>
      ))}
      <button type="button" onClick={add} className="btn btn-soft" style={{ width: "100%" }}>
        + Add project entry
      </button>
    </div>
  );
}
