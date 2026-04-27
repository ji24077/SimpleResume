/**
 * Find a bullet matching `original` inside a ResumeData and return a deep copy
 * with that bullet replaced by `replacement`.
 *
 * Match strategy (in order):
 *   1. Exact equality
 *   2. Case-insensitive whitespace-normalized
 *   3. First-50-character prefix (case-insensitive, normalized)
 *
 * Returns `{ rd, found }`. When `found` is false the input is returned
 * unchanged so callers can show an error without losing state.
 */

import type { ResumeData, ExperienceEntry, ProjectEntry } from "@/lib/types";

function norm(s: string): string {
  return s.replace(/\s+/g, " ").trim().toLowerCase();
}

/** Aggressive normalization: drop punctuation entirely so the matcher tolerates
 *  comma / period / dash drift between the LLM-echoed `original_text` and the
 *  exact bullet stored in resumeData. Used as a fallback after `norm`. */
function normLoose(s: string): string {
  return s
    .replace(/[\p{P}\p{S}]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function matches(bullet: string, original: string): boolean {
  if (bullet === original) return true;

  const a = norm(bullet);
  const b = norm(original);
  if (a === b) return true;

  const al = normLoose(bullet);
  const bl = normLoose(original);
  if (al === bl) return true;

  if (al.length >= 24 && bl.length >= 24) {
    // First 50 chars (loose) — survives leading-bullet glyphs and small edits.
    if (al.slice(0, 50) === bl.slice(0, 50)) return true;
    // Containment — handles cases where one side has a trailing period or
    // wrapper text the LLM inserted/removed.
    if (al.includes(bl) || bl.includes(al)) return true;
    // First 6 words (loose) — final fallback for "same bullet, mid-sentence
    // edits" without false-positive crosstalk between unrelated bullets.
    const aw = al.split(" ").slice(0, 6).join(" ");
    const bw = bl.split(" ").slice(0, 6).join(" ");
    if (aw === bw && aw.length >= 18) return true;
  }
  return false;
}

export type ApplyResult = { rd: ResumeData; found: boolean };

export function applyBulletRewrite(
  rd: ResumeData,
  original: string,
  replacement: string,
): ApplyResult {
  if (!original || !replacement) return { rd, found: false };
  let found = false;

  const patchEntries = <T extends ExperienceEntry | ProjectEntry>(arr: T[]): T[] =>
    arr.map((entry) => {
      if (found) return entry;
      const idx = entry.bullets.findIndex((b) => matches(b, original));
      if (idx === -1) return entry;
      const next = entry.bullets.slice();
      next[idx] = replacement;
      found = true;
      return { ...entry, bullets: next } as T;
    });

  const experience = patchEntries(rd.experience);
  if (found) {
    return {
      rd: { ...rd, experience },
      found: true,
    };
  }

  const projects = patchEntries(rd.projects);
  if (found) {
    return {
      rd: { ...rd, projects },
      found: true,
    };
  }

  return { rd, found: false };
}
