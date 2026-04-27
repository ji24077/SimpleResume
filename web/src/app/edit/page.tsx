"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ResumeForm from "@/components/builder/ResumeForm";
import { useReviewSession } from "@/lib/reviewSession";
import { submitStructuredGenerate } from "@/lib/upload";
import type { ResumeData } from "@/lib/types";

export default function EditPage() {
  const router = useRouter();
  const session = useReviewSession();
  const [hydrated, setHydrated] = useState(false);
  const [draft, setDraft] = useState<ResumeData | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!session.parse && !session.resumeData) {
      router.replace("/");
      return;
    }
    setDraft(session.resumeData ?? session.parse?.resume_data ?? null);
  }, [hydrated, session.parse, session.resumeData, router]);

  if (!hydrated || !draft) {
    return (
      <main className="main">
        <div className="container">
          <div className="card" style={{ padding: 28 }}>
            <span className="font-mono muted">Loading…</span>
          </div>
        </div>
      </main>
    );
  }

  const onSubmit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      session.setResumeData(draft);
      const result = await submitStructuredGenerate(draft, session.pagePolicy, (m) =>
        setProgress(m),
      );
      session.setGenerate(result);
      router.push("/review");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setSubmitting(false);
      setProgress(null);
    }
  };

  return (
    <main className="main fade-in">
      <div className="container" style={{ maxWidth: 880 }}>
        <ResumeForm
          value={draft}
          onChange={setDraft}
          onSubmit={onSubmit}
          onBack={() => router.push("/")}
          warnings={session.parse?.parse_warnings ?? []}
          submitting={submitting}
        />

        {progress && (
          <div className="card fade-in" style={{ marginTop: 14 }}>
            <span className="font-mono muted" style={{ fontSize: 12 }}>
              {progress}
            </span>
          </div>
        )}
        {error && (
          <div
            className="card fade-in"
            style={{
              marginTop: 14,
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
    </main>
  );
}
