"use client";

import { ResumeHeader, ResumeHeaderLink } from "@/lib/types";

type HeaderSectionProps = {
  header: ResumeHeader;
  onChange: (next: ResumeHeader) => void;
};

const FIELD_BASE = "input";

export default function HeaderSection({ header, onChange }: HeaderSectionProps) {
  const setField = <K extends keyof ResumeHeader>(key: K, value: ResumeHeader[K]) => {
    onChange({ ...header, [key]: value });
  };
  const updateLink = (i: number, patch: Partial<ResumeHeaderLink>) => {
    const next = header.links.map((l, idx) => (idx === i ? { ...l, ...patch } : l));
    setField("links", next);
  };
  const removeLink = (i: number) => {
    setField(
      "links",
      header.links.filter((_, idx) => idx !== i),
    );
  };
  const addLink = () => {
    setField("links", [...header.links, { label: "", url: "" }]);
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="t-label mb-1 block">Name</span>
          <input
            type="text"
            value={header.name}
            onChange={(e) => setField("name", e.target.value)}
            placeholder="Jane Doe"
            className={FIELD_BASE}
          />
        </label>
        <label className="block">
          <span className="t-label mb-1 block">Email</span>
          <input
            type="email"
            value={header.email}
            onChange={(e) => setField("email", e.target.value)}
            placeholder="jane@example.com"
            className={FIELD_BASE}
          />
        </label>
        <label className="block">
          <span className="t-label mb-1 block">Phone</span>
          <input
            type="tel"
            value={header.phone}
            onChange={(e) => setField("phone", e.target.value)}
            placeholder="+1 555 123 4567"
            className={FIELD_BASE}
          />
        </label>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="t-label">Links</span>
          <button type="button" onClick={addLink} className="btn btn-soft btn-sm">
            + Add link
          </button>
        </div>
        {header.links.length === 0 ? (
          <p className="font-mono muted" style={{ fontSize: 11 }}>
            No links yet (LinkedIn, GitHub, portfolio…).
          </p>
        ) : (
          <div className="space-y-2">
            {header.links.map((link, i) => (
              <div key={i} className="grid gap-2 sm:grid-cols-[1fr_2fr_auto]">
                <input
                  type="text"
                  value={link.label}
                  onChange={(e) => updateLink(i, { label: e.target.value })}
                  placeholder="LinkedIn"
                  className={FIELD_BASE}
                />
                <input
                  type="url"
                  value={link.url}
                  onChange={(e) => updateLink(i, { url: e.target.value })}
                  placeholder="https://linkedin.com/in/you"
                  className={FIELD_BASE}
                />
                <button
                  type="button"
                  onClick={() => removeLink(i)}
                  aria-label={`Remove link ${i + 1}`}
                  className="btn btn-soft btn-sm"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
