"use client";

import { SkillsBlock } from "@/lib/types";

type SkillsSectionProps = {
  skills: SkillsBlock;
  onChange: (next: SkillsBlock) => void;
};

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
      <span className="t-label mb-1 block">{label}</span>
      <input
        type="text"
        value={value.join(", ")}
        onChange={(e) => onChange(parseCsv(e.target.value))}
        placeholder={placeholder}
        className="input"
      />
      {value.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {value.map((item, i) => (
            <span
              key={`${item}-${i}`}
              className="font-mono"
              style={{
                background: "var(--surface-2)",
                color: "var(--fg-2)",
                border: "1px solid var(--border)",
                borderRadius: 999,
                padding: "2px 10px",
                fontSize: 11,
              }}
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
      <p className="font-mono muted" style={{ fontSize: 11 }}>
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
