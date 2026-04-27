"use client";

import { useState } from "react";
import type { BulletAnalysis, RoleAnalysis } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";
import IssueTag from "./IssueTag";

function formatLabel(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function BulletCard({ bullet }: { bullet: BulletAnalysis }) {
  const [open, setOpen] = useState(false);
  const rubricEntries = Object.entries(bullet.rubrics);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-zinc-800/30"
      >
        <ScoreBadge score={bullet.composite_score} size="sm" />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-zinc-200">{bullet.text}</p>
          {bullet.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {bullet.tags.map((tag) => (
                <IssueTag key={tag} label={tag} />
              ))}
            </div>
          )}
        </div>
        <span className="mt-1 shrink-0 text-xs text-zinc-500">
          {open ? "▲" : "▼"}
        </span>
      </button>

      {open && (
        <div className="border-t border-zinc-800 px-4 py-4 space-y-4">
          {rubricEntries.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">
              {rubricEntries.map(([key, rubric]) => (
                <div
                  key={key}
                  className="flex items-start gap-2 rounded-lg border border-zinc-800/60 bg-zinc-950/30 px-3 py-2"
                >
                  <ScoreBadge score={rubric.score} size="sm" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-zinc-300">
                      {formatLabel(key)}
                    </p>
                    <p className="text-xs text-zinc-500">{rubric.reason}</p>
                    {rubric.suggestion && (
                      <p className="mt-0.5 text-xs text-zinc-600">
                        💡 {rubric.suggestion}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {bullet.strengths.length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-emerald-400">
                Strengths
              </h4>
              <ul className="space-y-1">
                {bullet.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-zinc-400">
                    <span className="text-emerald-400">✓</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {bullet.issues.length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-400">
                Issues
              </h4>
              <ul className="space-y-1">
                {bullet.issues.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-zinc-400">
                    <span className="text-amber-400">⚠</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="rounded-lg border border-zinc-800/60 bg-zinc-950/30 px-3 py-2">
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-sky-400">
              Repair Readiness
            </h4>
            <div className="grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2">
              <p className="text-zinc-400">
                <span className="text-zinc-500">Recoverability:</span>{" "}
                {bullet.repair_readiness.recoverability}
              </p>
              <p className="text-zinc-400">
                <span className="text-zinc-500">Ask-back priority:</span>{" "}
                {bullet.repair_readiness.ask_back_priority}
              </p>
              <p className="text-zinc-400">
                <span className="text-zinc-500">Revision gain:</span>{" "}
                {bullet.repair_readiness.revision_gain_potential.toFixed(1)}
              </p>
              {bullet.repair_readiness.missing_dimensions.length > 0 && (
                <p className="text-zinc-400 sm:col-span-2">
                  <span className="text-zinc-500">Missing:</span>{" "}
                  {bullet.repair_readiness.missing_dimensions.join(", ")}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function BulletAnalysisSection({
  bullets,
  roles,
}: {
  bullets: BulletAnalysis[];
  roles: RoleAnalysis[];
}) {
  if (!bullets.length) {
    return <p className="text-sm text-zinc-500">No bullet data available.</p>;
  }

  const roleMap = new Map(roles.map((r) => [r.id, r]));
  const grouped = new Map<string, BulletAnalysis[]>();
  for (const b of bullets) {
    const arr = grouped.get(b.role_id) ?? [];
    arr.push(b);
    grouped.set(b.role_id, arr);
  }

  return (
    <div className="space-y-6">
      {Array.from(grouped.entries()).map(([roleId, roleBullets]) => {
        const role = roleMap.get(roleId);
        return (
          <div key={roleId}>
            <h3 className="mb-3 text-sm font-medium text-zinc-300">
              {role
                ? `${role.company} — ${role.title}`
                : `Role ${roleId}`}
            </h3>
            <div className="space-y-2">
              {roleBullets.map((bullet) => (
                <BulletCard key={bullet.id} bullet={bullet} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
