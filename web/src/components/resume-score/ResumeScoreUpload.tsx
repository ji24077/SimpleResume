"use client";

import { useCallback, useRef, useState } from "react";
import type { ResumeScoreResponse } from "@/lib/types";

const PROGRESS_STEPS = [
  "Extracting text...",
  "Parsing structure...",
  "Running ATS checks...",
  "Scoring content...",
  "Preparing feedback...",
];

interface ResumeScoreUploadProps {
  onScore: (result: ResumeScoreResponse) => void;
  loading: boolean;
  setLoading: (v: boolean) => void;
}

export default function ResumeScoreUpload({
  onScore,
  loading,
  setLoading,
}: ResumeScoreUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [paste, setPaste] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [progressIdx, setProgressIdx] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearProgress = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setProgressIdx(0);
  }, []);

  const startProgress = useCallback(() => {
    setProgressIdx(0);
    intervalRef.current = setInterval(() => {
      setProgressIdx((prev) =>
        prev < PROGRESS_STEPS.length - 1 ? prev + 1 : prev,
      );
    }, 3000);
  }, []);

  const canSubmit = Boolean(file || paste.trim());

  const onSubmit = useCallback(async () => {
    setError(null);
    setLoading(true);
    startProgress();

    try {
      let res: Response;
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        if (jobDescription.trim()) fd.append("job_description", jobDescription);
        res = await fetch("/api/resume-score", { method: "POST", body: fd });
      } else {
        res = await fetch("/api/resume-score", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: paste,
            ...(jobDescription.trim() && { job_description: jobDescription }),
          }),
        });
      }

      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        setError(
          typeof json.detail === "string"
            ? json.detail
            : JSON.stringify(json.detail || json) || res.statusText,
        );
        return;
      }

      const data = (await res.json()) as ResumeScoreResponse;
      onScore(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
      clearProgress();
    }
  }, [file, paste, jobDescription, onScore, setLoading, startProgress, clearProgress]);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-8">
      <h2 className="mb-2 text-sm font-medium text-zinc-300">
        Upload or paste your resume
      </h2>
      <p className="mb-6 text-sm text-zinc-500">
        PDF or plain text. We analyze structure, content quality, ATS
        compatibility, and provide a detailed score breakdown.
      </p>

      <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-zinc-700 bg-zinc-900 px-6 py-12 transition hover:border-sky-600/50 hover:bg-zinc-800/50">
        <input
          type="file"
          accept=".pdf,.txt"
          className="hidden"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            if (e.target.files?.[0]) setPaste("");
            setError(null);
          }}
        />
        <span className="text-sm text-zinc-400">
          {file ? file.name : "Drop file or click to choose"}
        </span>
      </label>

      <p className="mt-4 text-center text-xs text-zinc-600">or</p>

      <textarea
        value={paste}
        onChange={(e) => {
          setPaste(e.target.value);
          if (e.target.value) setFile(null);
          setError(null);
        }}
        placeholder="Paste resume text here…"
        rows={8}
        className="mt-4 w-full resize-y rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600"
      />

      <div className="mt-6 space-y-2 rounded-xl border border-zinc-800 bg-zinc-950/50 px-4 py-4">
        <p className="text-xs font-medium text-zinc-400">
          Job description (optional)
        </p>
        <textarea
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          placeholder="Paste the target job description for tailored scoring…"
          rows={4}
          className="w-full resize-y rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600"
        />
      </div>

      {loading && (
        <p className="mt-4 rounded-lg border border-sky-900/40 bg-sky-950/30 px-3 py-2 text-sm text-sky-200/95">
          {PROGRESS_STEPS[progressIdx]}
        </p>
      )}

      {error && (
        <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <button
        type="button"
        disabled={!canSubmit || loading}
        onClick={onSubmit}
        className="mt-6 w-full rounded-xl bg-sky-600 py-3 text-sm font-medium text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? PROGRESS_STEPS[progressIdx] : "Score My Resume"}
      </button>
    </div>
  );
}
