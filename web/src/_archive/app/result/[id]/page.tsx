"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { ReviewResponse } from "@/lib/types";
import ReviewWorkspace from "@/components/resume-review/ReviewWorkspace";

export default function ResultPage({ params }: { params: { id: string } }) {
  const [review, setReview] = useState<ReviewResponse | null>(null);
  void setReview; // TODO: will be used when persistence is implemented
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // TODO: Fetch review data by resume_id when persistence is implemented
    // For now, show a placeholder with a link to the review page
    setLoading(false);
    setError(
      "Direct result loading by ID is not yet supported. Use the Resume Review page to upload and review."
    );
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-sky-500 border-t-transparent" />
          <p className="text-sm text-zinc-400">Loading review for {params.id}…</p>
        </div>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-bold">Resume Review</h1>
          <p className="mt-2 text-zinc-400">
            Result ID: <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-sm">{params.id}</code>
          </p>
          {error && <p className="mt-4 text-sm text-zinc-500">{error}</p>}
          <div className="mt-6 flex justify-center gap-3">
            <Link
              href="/resume-review"
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
            >
              Go to Resume Review
            </Link>
            <Link
              href="/"
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800"
            >
              Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden">
      <ReviewWorkspace review={review} pdfUrl={null} />
    </div>
  );
}
