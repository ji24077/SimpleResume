"use client";

import { SkillsBlock } from "@/lib/types";

type SkillsSectionProps = {
  skills: SkillsBlock;
  onChange: (next: SkillsBlock) => void;
};

const FIELD_BASE =
  "w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600";

const parseCsv = (value: string): string[] =>
  value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

type SkillRowProps = {
  label: string;
  placeholder: string;
  value: string[];
  onChange: (next: string[]) => void;
};

function SkillRow({ label, placeholder, value, onChange }: SkillRowProps) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs uppercase tracking-wider text-zinc-500">{label}</span>
      <input
        type="text"
        value={value.join(", ")}
        onChange={(e) => onChange(parseCsv(e.target.value))}
        placeholder={placeholder}
        className={FIELD_BASE}
      />
      {value.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {value.map((item, i) => (
            <span
              key={`${item}-${i}`}
              className="rounded-full border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-xs text-zinc-300"
            >
              {item}
            </span>
          ))}
        </div>
      )}
    </label>
  );
}

export default function SkillsSection({ skills, onChange }: SkillsSectionProps) {
  const setField = <K extends keyof SkillsBlock>(key: K, value: SkillsBlock[K]) => {
    onChange({ ...skills, [key]: value });
  };
  return (
    <div className="space-y-3">
      <p className="text-xs text-zinc-500">
        Comma-separated. Example: <code>Python, TypeScript, Go</code>
      </p>
      <SkillRow
        label="Languages"
        placeholder="Python, TypeScript, Go"
        value={skills.languages}
        onChange={(v) => setField("languages", v)}
      />
      <SkillRow
        label="Frameworks"
        placeholder="React, Next.js, FastAPI"
        value={skills.frameworks}
        onChange={(v) => setField("frameworks", v)}
      />
      <SkillRow
        label="Tools"
        placeholder="Docker, Git, AWS"
        value={skills.tools}
        onChange={(v) => setField("tools", v)}
      />
    </div>
  );
}
