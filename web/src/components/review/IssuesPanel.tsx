"use client";

import { useMemo, useState } from "react";
import type { BulletChatMessage, ReviewIssue } from "@/lib/types";
import { useReviewSession } from "@/lib/reviewSession";
import IssueCard from "./IssueCard";

type Props = {
  issues: ReviewIssue[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  /** Apply: returns true if the resume was patched and the PDF re-rendered. The
   *  optional second arg is the chat-refined suggestion text to use instead of
   *  `issue.suggested_text`. */
  onApplyIssue?: (
    issue: ReviewIssue,
    suggestedTextOverride?: string,
  ) => Promise<boolean> | boolean;
  /** Undo a previously-applied fix — swap the suggested text back to original in the resume. */
  onUndoApply?: (issue: ReviewIssue) => Promise<boolean> | boolean;
};

export default function IssuesPanel({
  issues,
  loading,
  selectedId,
  onSelect,
  onApplyIssue,
  onUndoApply,
}: Props) {
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [errorById, setErrorById] = useState<Record<string, string>>({});
  const { issueChat, issueRefined, setIssueChat, setIssueRefined, clearIssueChat } =
    useReviewSession();

  const issueById = useMemo(() => {
    const m = new Map<string, ReviewIssue>();
    issues.forEach((i) => m.set(i.id, i));
    return m;
  }, [issues]);

  const active = issues.filter((i) => !appliedIds.has(i.id) && !dismissedIds.has(i.id));
  const applied = Array.from(appliedIds)
    .map((id) => issueById.get(id))
    .filter((i): i is ReviewIssue => !!i);
  const dismissed = Array.from(dismissedIds)
    .map((id) => issueById.get(id))
    .filter((i): i is ReviewIssue => !!i);

  const clearError = (id: string) =>
    setErrorById((m) => {
      const next = { ...m };
      delete next[id];
      return next;
    });

  const apply = async (issue: ReviewIssue) => {
    setPendingId(issue.id);
    clearError(issue.id);
    try {
      const override = issueRefined[issue.id];
      const ok = onApplyIssue ? await onApplyIssue(issue, override) : true;
      if (ok) {
        setAppliedIds((s) => new Set([...s, issue.id]));
      } else {
        setErrorById((m) => ({
          ...m,
          [issue.id]: "Couldn't locate that bullet — try again.",
        }));
      }
    } catch (e) {
      setErrorById((m) => ({
        ...m,
        [issue.id]: e instanceof Error ? e.message : "Apply failed.",
      }));
    } finally {
      setPendingId(null);
    }
  };

  const cardChatProps = (iss: ReviewIssue) => ({
    currentSuggestion: issueRefined[iss.id] ?? iss.suggested_text,
    chatHistory: (issueChat[iss.id] ?? []) as BulletChatMessage[],
    onSuggestionUpdate: (text: string) => setIssueRefined(iss.id, text),
    onHistoryUpdate: (next: BulletChatMessage[]) => setIssueChat(iss.id, next),
    onResetSuggestion: () => clearIssueChat(iss.id),
  });

  const undoApply = async (issue: ReviewIssue) => {
    setPendingId(issue.id);
    clearError(issue.id);
    try {
      const ok = onUndoApply ? await onUndoApply(issue) : true;
      if (ok) {
        setAppliedIds((s) => {
          const next = new Set(s);
          next.delete(issue.id);
          return next;
        });
      } else {
        setErrorById((m) => ({
          ...m,
          [issue.id]: "Couldn't undo — bullet may have been edited elsewhere.",
        }));
      }
    } catch (e) {
      setErrorById((m) => ({
        ...m,
        [issue.id]: e instanceof Error ? e.message : "Undo failed.",
      }));
    } finally {
      setPendingId(null);
    }
  };

  const undoDismiss = (issue: ReviewIssue) => {
    setDismissedIds((s) => {
      const next = new Set(s);
      next.delete(issue.id);
      return next;
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="row between" style={{ padding: "0 4px", gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div className="t-label">Issues & suggestions</div>
          <div className="font-mono muted" style={{ fontSize: 11, marginTop: 2 }}>
            {loading
              ? "loading…"
              : `${active.length} active · ${applied.length} applied · ${dismissed.length} dismissed`}
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={loading || active.length === 0 || pendingId !== null}
          onClick={async () => {
            for (const iss of active) {
              if (!iss.suggested_text) continue;
              await apply(iss);
            }
          }}
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

      {!loading && active.length === 0 && applied.length === 0 && dismissed.length === 0 && (
        <div className="card" style={{ padding: 18, textAlign: "center" }}>
          <p className="muted" style={{ fontSize: 13 }}>
            No issues flagged. Either your résumé is clean, or the reviewer is still warming up.
          </p>
        </div>
      )}

      {!loading &&
        active.map((iss, idx) => (
          <IssueCard
            key={iss.id}
            issue={iss}
            index={idx}
            selected={selectedId === iss.id}
            applied={false}
            pending={pendingId === iss.id}
            error={errorById[iss.id]}
            onSelect={() => onSelect(iss.id === selectedId ? null : iss.id)}
            onApply={() => apply(iss)}
            onDismiss={() => setDismissedIds((s) => new Set([...s, iss.id]))}
            {...cardChatProps(iss)}
          />
        ))}

      {!loading && (applied.length > 0 || dismissed.length > 0) && (
        <div
          className="row"
          style={{
            gap: 8,
            margin: "8px 0 2px",
            padding: "0 4px",
            color: "var(--fg-5)",
          }}
        >
          <span className="t-label" style={{ fontSize: 10 }}>
            Resolved
          </span>
          <span style={{ flex: 1, height: 1, background: "var(--border)" }} />
        </div>
      )}

      {!loading &&
        applied.map((iss, idx) => (
          <IssueCard
            key={`applied-${iss.id}`}
            issue={iss}
            index={active.length + idx}
            selected={selectedId === iss.id}
            applied
            pending={pendingId === iss.id}
            error={errorById[iss.id]}
            onSelect={() => onSelect(iss.id === selectedId ? null : iss.id)}
            onApply={() => apply(iss)}
            onDismiss={() => setDismissedIds((s) => new Set([...s, iss.id]))}
            onUndo={() => undoApply(iss)}
            undoLabel="Undo apply"
          />
        ))}

      {!loading &&
        dismissed.map((iss, idx) => (
          <IssueCard
            key={`dismissed-${iss.id}`}
            issue={iss}
            index={active.length + applied.length + idx}
            selected={selectedId === iss.id}
            applied={false}
            dismissed
            pending={pendingId === iss.id}
            error={errorById[iss.id]}
            onSelect={() => onSelect(iss.id === selectedId ? null : iss.id)}
            onApply={() => apply(iss)}
            onDismiss={() => setDismissedIds((s) => new Set([...s, iss.id]))}
            onUndo={() => undoDismiss(iss)}
            undoLabel="Undo dismiss"
          />
        ))}
    </div>
  );
}
