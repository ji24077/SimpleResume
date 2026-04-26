"use client";

import Link from "next/link";
import { useState } from "react";
import type { ResumeScoreResponse } from "@/lib/types";
import ResumeScoreUpload from "@/components/resume-score/ResumeScoreUpload";
import ResumeScoreOverview from "@/components/resume-score/ResumeScoreOverview";
import ResumeRubricGrid from "@/components/resume-score/ResumeRubricGrid";
import RoleAnalysisSection from "@/components/resume-score/RoleAnalysisSection";
import BulletAnalysisSection from "@/components/resume-score/BulletAnalysisSection";
import AtsAuditSection from "@/components/resume-score/AtsAuditSection";
import RecommendationsSection from "@/components/resume-score/RecommendationsSection";

const TABS = [
  "Overview",
  "Rubrics",
  "Roles",
  "Bullets",
  "ATS Audit",
  "Recommendations",
] as const;

type Tab = (typeof TABS)[number];

const RUBRIC_EXAMPLES = [
  "Content quality & impact metrics",
  "ATS compatibility & parseability",
  "Structure, hierarchy & formatting",
  "Bullet specificity & action verbs",
  "Keyword coverage & relevance",
  "Repair readiness & revision potential",
];

export default function ResumeScorePage() {
  const [result, setResult] = useState<ResumeScoreResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  const reset = () => {
    setResult(null);
    setActiveTab("Overview");
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-lg font-semibold tracking-tight text-white">
                  Resume Score
                </h1>
                <Link
                  href="/"
                  className="rounded-lg border border-zinc-700 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:border-emerald-700 hover:text-emerald-300"
                >
                  Resume Generator
                </Link>
              </div>
              <p className="text-xs text-zinc-500">
                Deep analysis · Rubric scoring · ATS audit · Actionable fixes
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10">
        {!result ? (
          <div className="space-y-12">
            <section
              className="relative overflow-hidden rounded-3xl border border-zinc-800/80 bg-gradient-to-b from-zinc-900/90 to-zinc-950 px-6 py-12 md:px-10 md:py-16"
              aria-labelledby="score-hero-heading"
            >
              <div
                className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-sky-500/10 blur-3xl"
                aria-hidden
              />
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-500/90">
                Detailed analysis · Rubric-based scoring
              </p>
              <h2
                id="score-hero-heading"
                className="mt-3 max-w-4xl text-3xl font-bold leading-tight tracking-tight text-white md:text-4xl md:leading-tight"
              >
                Know exactly{" "}
                <span className="bg-gradient-to-r from-sky-300 to-sky-500 bg-clip-text text-transparent">
                  where your resume stands
                </span>{" "}
                — and how to improve it
              </h2>
              <p className="mt-5 max-w-3xl text-base leading-relaxed text-zinc-400 md:text-lg">
                Upload your resume and get a comprehensive score breakdown across
                multiple dimensions — content quality, ATS compatibility,
                structure, and more. Every bullet is analyzed individually with
                specific, actionable suggestions.
              </p>

              <div className="mt-8">
                <h3 className="mb-4 text-sm font-medium text-zinc-300">
                  What we evaluate
                </h3>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {RUBRIC_EXAMPLES.map((item) => (
                    <div
                      key={item}
                      className="flex items-center gap-2 rounded-xl border border-zinc-800/80 bg-zinc-950/50 px-4 py-3"
                    >
                      <span className="text-sky-400" aria-hidden>
                        ✓
                      </span>
                      <span className="text-sm text-zinc-300">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <ResumeScoreUpload
              onScore={setResult}
              loading={loading}
              setLoading={setLoading}
            />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={reset}
                className="rounded-lg border border-zinc-600 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800"
              >
                Score Another
              </button>
            </div>

            <div className="flex gap-1 overflow-x-auto rounded-lg bg-zinc-900 p-1">
              {TABS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setActiveTab(t)}
                  className={`shrink-0 rounded-md px-3 py-2 text-sm font-medium transition ${
                    activeTab === t
                      ? "bg-zinc-800 text-white"
                      : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {activeTab === "Overview" && (
              <ResumeScoreOverview result={result} />
            )}
            {activeTab === "Rubrics" && (
              <ResumeRubricGrid rubrics={result.resume_rubrics} />
            )}
            {activeTab === "Roles" && (
              <RoleAnalysisSection roles={result.roles} />
            )}
            {activeTab === "Bullets" && (
              <BulletAnalysisSection
                bullets={result.bullets}
                roles={result.roles}
              />
            )}
            {activeTab === "ATS Audit" && (
              <AtsAuditSection audit={result.ats_audit} />
            )}
            {activeTab === "Recommendations" && (
              <RecommendationsSection
                recommendations={result.recommendations}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
