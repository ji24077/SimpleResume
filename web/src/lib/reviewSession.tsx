"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { GenerateResponse, PagePolicy, ParseResponse, ResumeData } from "@/lib/types";

const STORAGE_KEY = "simpleresume-session-v1";

export type ReviewSessionState = {
  sessionId: string | null;
  generate: GenerateResponse | null;
  parse: ParseResponse | null;
  resumeData: ResumeData | null;
  pagePolicy: PagePolicy;
  /** Captures latest source so /review can reload generate if needed */
  rawText: string | null;
};

type ReviewSessionContextValue = ReviewSessionState & {
  setGenerate: (r: GenerateResponse | null) => void;
  setParse: (p: ParseResponse | null) => void;
  setResumeData: (r: ResumeData | null) => void;
  setPagePolicy: (p: PagePolicy) => void;
  setRawText: (t: string | null) => void;
  startSession: () => string;
  reset: () => void;
};

const ReviewSessionContext = createContext<ReviewSessionContextValue | null>(null);

const EMPTY: ReviewSessionState = {
  sessionId: null,
  generate: null,
  parse: null,
  resumeData: null,
  pagePolicy: "strict_one_page",
  rawText: null,
};

function makeId() {
  return `s_${Math.random().toString(36).slice(2, 10)}_${Date.now().toString(36)}`;
}

function loadFromStorage(): ReviewSessionState {
  if (typeof window === "undefined") return EMPTY;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Partial<ReviewSessionState>;
    return { ...EMPTY, ...parsed };
  } catch {
    return EMPTY;
  }
}

function saveToStorage(state: ReviewSessionState) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* sessionStorage may be full; drop silently */
  }
}

export function ReviewSessionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ReviewSessionState>(EMPTY);

  useEffect(() => {
    setState(loadFromStorage());
  }, []);

  useEffect(() => {
    if (state.sessionId) saveToStorage(state);
  }, [state]);

  const setGenerate = useCallback(
    (r: GenerateResponse | null) => setState((s) => ({ ...s, generate: r })),
    [],
  );
  const setParse = useCallback(
    (p: ParseResponse | null) => setState((s) => ({ ...s, parse: p })),
    [],
  );
  const setResumeData = useCallback(
    (r: ResumeData | null) => setState((s) => ({ ...s, resumeData: r })),
    [],
  );
  const setPagePolicy = useCallback(
    (p: PagePolicy) => setState((s) => ({ ...s, pagePolicy: p })),
    [],
  );
  const setRawText = useCallback(
    (t: string | null) => setState((s) => ({ ...s, rawText: t })),
    [],
  );
  const startSession = useCallback(() => {
    const id = makeId();
    setState({ ...EMPTY, sessionId: id });
    return id;
  }, []);
  const reset = useCallback(() => {
    setState(EMPTY);
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const value = useMemo<ReviewSessionContextValue>(
    () => ({
      ...state,
      setGenerate,
      setParse,
      setResumeData,
      setPagePolicy,
      setRawText,
      startSession,
      reset,
    }),
    [state, setGenerate, setParse, setResumeData, setPagePolicy, setRawText, startSession, reset],
  );

  return <ReviewSessionContext.Provider value={value}>{children}</ReviewSessionContext.Provider>;
}

export function useReviewSession(): ReviewSessionContextValue {
  const ctx = useContext(ReviewSessionContext);
  if (!ctx) throw new Error("useReviewSession must be used within ReviewSessionProvider");
  return ctx;
}
