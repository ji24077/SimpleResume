"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useReviewSession } from "@/lib/reviewSession";
import { useReviewBundle } from "@/lib/useReviewBundle";
import { applyBulletRewrite } from "@/lib/applyFix";
import type { ReviewIssue } from "@/lib/types";
import IssuesPanel from "@/components/review/IssuesPanel";
import PageHead from "@/components/review/PageHead";
import PdfPanel from "@/components/review/PdfPanel";
import RubricDrawer from "@/components/review/RubricDrawer";
import SaveBanner from "@/components/review/SaveBanner";
import ScoreChip from "@/components/review/ScoreChip";
import VerifyParseDrawer from "@/components/review/VerifyParseDrawer";

export default function ReviewPage() {
  return (
    <Suspense fallback={<ReviewPageFallback />}>
      <ReviewPageInner />
    </Suspense>
  );
}

function ReviewPageFallback() {
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

function ReviewPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const session = useReviewSession();
  const stage = params.get("stage");

  const [hydrated, setHydrated] = useState(false);
  const [rubricOpen, setRubricOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (stage === "verify" && session.parse) setDrawerOpen(true);
  }, [stage, session.parse]);

  useEffect(() => {
    if (!hydrated) return;
    if (!session.generate && !session.parse) {
      router.replace("/");
    }
  }, [hydrated, session.generate, session.parse, router]);

  const bundle = useReviewBundle({
    generate: session.generate,
    rawText: session.rawText,
  });

  const issues = bundle.review?.issues ?? [];

  const candidateName = useMemo(() => {
    if (session.resumeData?.header.name) return session.resumeData.header.name;
    const previewHeader = session.generate?.preview_sections?.[0]?.title;
    return previewHeader ?? "";
  }, [session.resumeData, session.generate]);

  const overall = bundle.score?.overall_score ?? null;
  const grade = bundle.score?.grade ?? null;

  const pagePolicy = session.pagePolicy;
  const replacePdf = bundle.replacePdf;
  const renderAndSwap = useCallback(
    async (rd: import("@/lib/types").ResumeData | null) => {
      if (!rd) return;
      const res = await fetch("/api/render-only", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_data: rd, page_policy: pagePolicy }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(typeof j.detail === "string" ? j.detail : "Render failed.");
      }
      const blob = await res.blob();
      replacePdf(blob);
    },
    [pagePolicy, replacePdf],
  );

  const onApplyIssue = useCallback(
    async (issue: ReviewIssue): Promise<boolean> => {
      const rd = session.resumeData;
      if (!rd) throw new Error("No structured résumé to patch.");
      if (!issue.suggested_text) return false;
      const { rd: patched, found } = applyBulletRewrite(
        rd,
        issue.original_text,
        issue.suggested_text,
      );
      if (!found) return false;
      session.setResumeData(patched);
      await renderAndSwap(patched);
      return true;
    },
    [session, renderAndSwap],
  );

  const onUndoApply = useCallback(
    async (issue: ReviewIssue): Promise<boolean> => {
      const rd = session.resumeData;
      if (!rd) throw new Error("No structured résumé to patch.");
      if (!issue.suggested_text || !issue.original_text) return false;
      // Swap suggested → original to restore the bullet.
      const { rd: patched, found } = applyBulletRewrite(
        rd,
        issue.suggested_text,
        issue.original_text,
      );
      if (!found) return false;
      session.setResumeData(patched);
      await renderAndSwap(patched);
      return true;
    },
    [session, renderAndSwap],
  );

  if (!hydrated) {
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

  return (
    <main className="main fade-in">
      <div className="container">
        <SaveBanner />

        <div className="page-head" style={{ marginBottom: 18 }}>
          <div className="head-l">
            <PageHead name={candidateName} issues={issues} />
          </div>
          <div className="head-r">
            <ScoreChip
              score={overall}
              grade={grade}
              expanded={rubricOpen}
              onToggle={() => setRubricOpen((v) => !v)}
              loading={bundle.scoreStatus === "loading"}
            />
            {session.parse && (
              <button
                type="button"
                className="btn btn-soft btn-sm"
                onClick={() => setDrawerOpen(true)}
              >
                Edit parsed data
              </button>
            )}
          </div>
        </div>

        {rubricOpen && (
          <RubricDrawer
            score={bundle.score}
            loading={bundle.scoreStatus === "loading"}
            onClose={() => setRubricOpen(false)}
          />
        )}

        {!session.generate && session.parse && (
          <div
            className="card"
            style={{
              padding: 24,
              textAlign: "center",
              background: "var(--surface-1)",
            }}
          >
            <div className="font-display" style={{ fontSize: 18, marginBottom: 6 }}>
              Confirm your details to generate
            </div>
            <p className="muted" style={{ fontSize: 13, marginBottom: 14 }}>
              We parsed your résumé. Review the fields, then we&apos;ll rewrite and compile.
            </p>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setDrawerOpen(true)}
            >
              Open verify-parse
            </button>
          </div>
        )}

        {session.generate && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 440px",
              gap: 20,
              alignItems: "start",
            }}
          >
            <PdfPanel
              pdfUrl={bundle.pdfUrl}
              pdfBlob={bundle.pdfBlob}
              pdfStatus={bundle.pdfStatus}
              pdfError={bundle.pdfError}
              latex={session.generate.latex_document}
              issues={issues}
              selectedId={selectedIssueId}
              onSelectIssue={setSelectedIssueId}
            />
            <IssuesPanel
              issues={issues}
              loading={bundle.reviewStatus === "loading"}
              selectedId={selectedIssueId}
              onSelect={setSelectedIssueId}
              onApplyIssue={onApplyIssue}
              onUndoApply={onUndoApply}
            />
          </div>
        )}
      </div>

      <VerifyParseDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </main>
  );
}
