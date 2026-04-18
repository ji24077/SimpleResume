"use client";

import { useState } from "react";
import type { RoleAnalysis } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

function formatLabel(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function RoleCard({ role }: { role: RoleAnalysis }) {
  const [open, setOpen] = useState(false);
  const rubricEntries = Object.entries(role.rubrics);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-4 text-left transition hover:bg-zinc-800/30"
      >
        <ScoreBadge score={role.composite_score} size="sm" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-zinc-100">
            {role.company}
            <span className="mx-1.5 text-zinc-600">|</span>
            {role.title}
          </p>
          <p className="text-xs text-zinc-500">{role.date_range}</p>
        </div>
        <span className="text-xs text-zinc-500">{open ? "▲" : "▼"}</span>
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
                  </div>
                </div>
              ))}
            </div>
          )}

          {role.strengths.length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-emerald-400">
                Strengths
              </h4>
              <ul className="space-y-1">
                {role.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-zinc-400">
                    <span className="text-emerald-400">✓</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {role.issues.length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-400">
                Issues
              </h4>
              <ul className="space-y-1">
                {role.issues.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-zinc-400">
                    <span className="text-amber-400">⚠</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function RoleAnalysisSection({
  roles,
}: {
  roles: RoleAnalysis[];
}) {
  if (!roles.length) {
    return (
      <p className="text-sm text-zinc-500">No role data available.</p>
    );
  }

  return (
    <div className="space-y-3">
      {roles.map((role) => (
        <RoleCard key={role.id} role={role} />
      ))}
    </div>
  );
}
