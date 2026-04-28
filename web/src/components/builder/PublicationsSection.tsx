"use client";

import { PublicationEntry } from "@/lib/types";
import EntryCard from "./EntryCard";

type PublicationsSectionProps = {
  publications: PublicationEntry[];
  onChange: (next: PublicationEntry[]) => void;
};

const EMPTY_PUBLICATION: PublicationEntry = {
  title: "",
  authors: [],
  self_name: "",
  venue: "",
  venue_short: "",
  year: "",
  type: "",
  status: "",
  link: "",
};

const splitAuthors = (raw: string): string[] =>
  raw
    .split(",")
    .map((a) => a.trim())
    .filter(Boolean);

export default function PublicationsSection({ publications, onChange }: PublicationsSectionProps) {
  const update = (i: number, patch: Partial<PublicationEntry>) => {
    onChange(publications.map((p, idx) => (idx === i ? { ...p, ...patch } : p)));
  };
  const remove = (i: number) => {
    onChange(publications.filter((_, idx) => idx !== i));
  };
  const add = () => {
    onChange([...publications, { ...EMPTY_PUBLICATION, authors: [] }]);
  };

  return (
    <div className="space-y-3">
      {publications.map((entry, i) => (
        <EntryCard
          key={i}
          heading={entry.title}
          subheading={entry.venue_short || entry.venue}
          onDelete={() => remove(i)}
          deleteLabel={`Remove publication entry ${i + 1}`}
        >
          <label className="block">
            <span className="t-label mb-1 block">Title</span>
            <input
              type="text"
              value={entry.title}
              onChange={(e) => update(i, { title: e.target.value })}
              placeholder="CyCLeGen: Cycle-Consistent Layout Prediction…"
              className="input"
            />
          </label>

          <label className="block">
            <span className="t-label mb-1 block">Authors (comma-separated, in order)</span>
            <textarea
              value={entry.authors.join(", ")}
              onChange={(e) => update(i, { authors: splitAuthors(e.target.value) })}
              placeholder="X. Shan, H. Shen, Y. Mao, A. Anand, Z. Tu"
              rows={2}
              className="input"
              style={{ resize: "vertical", lineHeight: 1.5 }}
            />
          </label>

          <label className="block">
            <span className="t-label mb-1 block">Your name as it appears in the author list</span>
            <input
              type="text"
              value={entry.self_name}
              onChange={(e) => update(i, { self_name: e.target.value })}
              placeholder="A. Anand"
              className="input"
            />
            <span className="muted" style={{ fontSize: 11 }}>
              Bolded in render. Must match exactly (case-insensitive).
            </span>
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="t-label mb-1 block">Venue (full, italic)</span>
              <input
                type="text"
                value={entry.venue}
                onChange={(e) => update(i, { venue: e.target.value })}
                placeholder="European Conference on Computer Vision"
                className="input"
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Venue short / abbrev (bold)</span>
              <input
                type="text"
                value={entry.venue_short}
                onChange={(e) => update(i, { venue_short: e.target.value })}
                placeholder="ECCV 2026"
                className="input"
              />
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block">
              <span className="t-label mb-1 block">Year</span>
              <input
                type="text"
                value={entry.year}
                onChange={(e) => update(i, { year: e.target.value })}
                placeholder="2026"
                className="input"
              />
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Type</span>
              <select
                value={entry.type}
                onChange={(e) => update(i, { type: e.target.value })}
                className="input"
              >
                <option value="">(none)</option>
                <option value="conference">Conference</option>
                <option value="journal">Journal</option>
                <option value="workshop">Workshop</option>
                <option value="preprint">Preprint</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label className="block">
              <span className="t-label mb-1 block">Status</span>
              <input
                type="text"
                value={entry.status}
                onChange={(e) => update(i, { status: e.target.value })}
                placeholder="Under review at"
                className="input"
              />
            </label>
          </div>

          <label className="block">
            <span className="t-label mb-1 block">Link (arXiv id, DOI, or URL)</span>
            <input
              type="text"
              value={entry.link}
              onChange={(e) => update(i, { link: e.target.value })}
              placeholder="arXiv:2603.14957"
              className="input"
            />
          </label>
        </EntryCard>
      ))}
      <button type="button" onClick={add} className="btn btn-soft" style={{ width: "100%" }}>
        + Add publication
      </button>
    </div>
  );
}
