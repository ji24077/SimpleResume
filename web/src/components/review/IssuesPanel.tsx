"use client";

import { useState } from "react";
import type { ReviewIssue } from "@/lib/types";
import IssueCard from "./IssueCard";

type Props = {
  issues: ReviewIssue[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
};

export default function IssuesPanel({ issues, loading, selectedId, onSelect }: Props) {
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  const visible = issues.filter((i) => !dismissedIds.has(i.id));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="row between" style={{ padding: "0 4px", gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div className="t-label">Issues & suggestions</div>
          <div className="font-mono muted" style={{ fontSize: 11, marginTop: 2 }}>
            {loading
              ? "loading…"
              : `${visible.length} item${visible.length === 1 ? "" : "s"} · ${appliedIds.size} applied`}
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={loading || visible.length === 0}
          onClick={() => setAppliedIds(new Set(visible.map((i) => i.id)))}
        >
          Apply all →
        </button>
      </div>

      {loading && (
        <>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card" style={{ padding: 14 }}>
              <div className="skeleton" style={{ height: 14, width: 120, marginBottom: 10 }} />
              <div className="skeleton" style={{ height: 10, marginBottom: 6 }} />
              <div className="skeleton" style={{ height: 10, width: "70%" }} />
            </div>
          ))}
        </>
      )}

      {!loading && visible.length === 0 && (
        <div className="card" style={{ padding: 18, textAlign: "center" }}>
          <p className="muted" style={{ fontSize: 13 }}>
            No issues flagged. Either your résumé is clean, or the reviewer is still warming up.
          </p>
        </div>
      )}

      {!loading &&
        visible.map((iss, idx) => (
          <IssueCard
            key={iss.id}
            issue={iss}
            index={idx}
            selected={selectedId === iss.id}
            applied={appliedIds.has(iss.id)}
            onSelect={() => onSelect(iss.id === selectedId ? null : iss.id)}
            onApply={() => setAppliedIds((s) => new Set([...s, iss.id]))}
            onDismiss={() => setDismissedIds((s) => new Set([...s, iss.id]))}
          />
        ))}
    </div>
  );
}
