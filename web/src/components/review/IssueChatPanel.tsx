"use client";

import { useState } from "react";
import type { BulletChatMessage, IssueCategory, IssueSeverity } from "@/lib/types";
import { submitBulletChat } from "@/lib/upload";

type Props = {
  issueId: string;
  originalText: string;
  /** Reviewer-vetted initial suggestion. Frozen across turns. */
  baselineSuggestion: string;
  /** Display-only current suggestion (for context only; not sent as ground truth). */
  currentSuggestion: string;
  history: BulletChatMessage[];
  sectionId?: string;
  bulletId?: string;
  severity?: IssueSeverity;
  category?: IssueCategory;
  onHistoryChange: (next: BulletChatMessage[]) => void;
  onProposedTextChange: (text: string) => void;
};

export default function IssueChatPanel({
  issueId,
  originalText,
  baselineSuggestion,
  currentSuggestion,
  history,
  sectionId,
  bulletId,
  severity,
  category,
  onHistoryChange,
  onProposedTextChange,
}: Props) {
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async () => {
    const text = draft.trim();
    if (!text || pending) return;
    setError(null);
    const userTurn: BulletChatMessage = { role: "user", content: text };
    const nextHistory = [...history, userTurn];
    onHistoryChange(nextHistory);
    setDraft("");
    setPending(true);
    try {
      const result = await submitBulletChat({
        issueId,
        originalText,
        baselineSuggestion,
        currentSuggestion,
        userMessage: text,
        history,
        sectionId,
        bulletId,
        severity,
        category,
      });
      const assistantTurn: BulletChatMessage = {
        role: "assistant",
        content:
          result.assistant_message ||
          (result.mode === "clarify" ? "Need a bit more info." : "Updated."),
      };
      onHistoryChange([...nextHistory, assistantTurn]);
      // Only update the diff on rewrite mode. Clarify keeps the diff frozen
      // and waits for the user's next answer.
      if (result.mode === "rewrite" && result.proposed_text) {
        onProposedTextChange(result.proposed_text);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed.");
      onHistoryChange(history);
    } finally {
      setPending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      style={{
        marginTop: 12,
        paddingTop: 12,
        borderTop: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      {history.length > 0 && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            maxHeight: 240,
            overflowY: "auto",
            paddingRight: 2,
          }}
        >
          {history.map((m, i) => {
            const isUser = m.role === "user";
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: isUser ? "flex-end" : "flex-start",
                }}
              >
                <span
                  style={{
                    maxWidth: "78%",
                    padding: "6px 10px",
                    fontSize: 12,
                    lineHeight: 1.45,
                    borderRadius: 12,
                    borderBottomRightRadius: isUser ? 3 : 12,
                    borderBottomLeftRadius: isUser ? 12 : 3,
                    background: isUser ? "var(--accent-soft)" : "var(--bg-2)",
                    color: isUser ? "var(--accent)" : "var(--fg-2)",
                    border: isUser ? "1px solid transparent" : "1px solid var(--border)",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {m.content}
                </span>
              </div>
            );
          })}
          {pending && (
            <div style={{ display: "flex", justifyContent: "flex-start" }}>
              <span
                style={{
                  padding: "6px 10px",
                  fontSize: 12,
                  borderRadius: 12,
                  borderBottomLeftRadius: 3,
                  background: "var(--bg-2)",
                  color: "var(--fg-5)",
                  border: "1px solid var(--border)",
                  fontStyle: "italic",
                }}
              >
                thinking…
              </span>
            </div>
          )}
        </div>
      )}

      <div
        style={{
          display: "flex",
          gap: 6,
          alignItems: "flex-end",
        }}
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="any suggestions?"
          rows={1}
          disabled={pending}
          style={{
            flex: 1,
            minHeight: 32,
            maxHeight: 96,
            padding: "6px 10px",
            border: "1px solid var(--border)",
            borderRadius: 6,
            background: "var(--bg-1)",
            color: "var(--fg-1)",
            fontSize: 13,
            lineHeight: 1.4,
            resize: "vertical",
          }}
        />
        <button
          type="button"
          className="btn btn-soft btn-sm"
          disabled={pending || !draft.trim()}
          onClick={send}
        >
          {pending ? "…" : "Send"}
        </button>
      </div>

      {error && (
        <div
          style={{
            fontSize: 12,
            color: "var(--error)",
            background: "var(--error-bg)",
            border: "1px solid transparent",
            borderLeft: "2px solid var(--error)",
            padding: "6px 10px",
            borderRadius: 4,
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
