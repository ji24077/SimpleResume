"use client";

import { useEffect, useState } from "react";
import ResumeForm from "@/components/builder/ResumeForm";
import { useReviewSession } from "@/lib/reviewSession";
import { submitStructuredGenerate } from "@/lib/upload";
import type { ResumeData } from "@/lib/types";

type Props = {
  open: boolean;
  onClose: () => void;
};

export default function VerifyParseDrawer({ open, onClose }: Props) {
  const session = useReviewSession();
  const [draft, setDraft] = useState<ResumeData | null>(session.resumeData);
  const [progress, setProgress] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) setDraft(session.resumeData);
  }, [open, session.resumeData]);

  if (!open || !draft) return null;

  const onSubmit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const result = await submitStructuredGenerate(draft, session.pagePolicy, (m) => setProgress(m));
      session.setResumeData(draft);
      session.setGenerate(result);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setSubmitting(false);
      setProgress(null);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        justifyContent: "flex-end",
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(720px, 100%)",
          height: "100%",
          background: "var(--canvas)",
          borderLeft: "1px solid var(--border)",
          boxShadow: "var(--shadow-modal)",
          overflowY: "auto",
          paddingBottom: 80,
        }}
      >
        <div
          className="row between"
          style={{
            position: "sticky",
            top: 0,
            zIndex: 10,
            background: "var(--canvas)",
            borderBottom: "1px solid var(--border)",
            padding: "14px 22px",
          }}
        >
          <div>
            <div className="t-eyebrow">verify-parse</div>
            <div className="font-display" style={{ fontSize: 18, fontWeight: 600 }}>
              Review what we read
            </div>
          </div>
          <button type="button" className="btn btn-soft btn-sm" onClick={onClose} disabled={submitting}>
            Close
          </button>
        </div>

        <ResumeForm
          value={draft}
          onChange={setDraft}
          onSubmit={onSubmit}
          warnings={session.parse?.parse_warnings ?? []}
          submitting={submitting}
        />

        {progress && (
          <div className="card" style={{ margin: "0 22px 22px" }}>
            <span className="font-mono muted" style={{ fontSize: 12 }}>
              {progress}
            </span>
          </div>
        )}
        {error && (
          <div
            className="card"
            style={{
              margin: "0 22px 22px",
              background: "var(--error-bg)",
              borderColor: "transparent",
              borderLeft: "3px solid var(--error)",
              color: "var(--error)",
            }}
          >
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
