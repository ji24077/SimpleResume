"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useReviewSession } from "@/lib/reviewSession";
import {
  pasteContactGaps,
  submitLegacyGenerate,
  submitParse,
} from "@/lib/upload";

const FEATURE_PARSE_REVIEW = process.env.NEXT_PUBLIC_FEATURE_PARSE_REVIEW === "true";

export default function DropZone() {
  const router = useRouter();
  const session = useReviewSession();
  const fileRef = useRef<HTMLInputElement>(null);

  const [drag, setDrag] = useState(false);
  const [showPaste, setShowPaste] = useState(false);
  const [paste, setPaste] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactLinkedin, setContactLinkedin] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startFlow = useCallback(
    async (file: File | null, pasteText: string) => {
      setError(null);
      setProgress(null);
      setLoading(true);
      try {
        if (!file) {
          const { needEmail, needLinkedin } = pasteContactGaps(pasteText);
          if (needEmail && !contactEmail.trim()) {
            throw new Error(
              "We couldn't find an email in your pasted text. Add one in the contact field, or include it in the resume.",
            );
          }
          if (needLinkedin && !contactLinkedin.trim()) {
            throw new Error(
              "We couldn't find a LinkedIn URL in your pasted text. Add your profile URL or include a linkedin.com link.",
            );
          }
        }

        session.reset();
        session.startSession();
        session.setRawText(pasteText || null);

        if (FEATURE_PARSE_REVIEW) {
          const parsed = await submitParse({
            file,
            paste: pasteText,
            contactEmail,
            contactLinkedin,
            contactPhone,
          });
          session.setParse(parsed);
          session.setResumeData(parsed.resume_data);
          router.push("/review?stage=verify");
          return;
        }

        const result = await submitLegacyGenerate(
          {
            file,
            paste: pasteText,
            pagePolicy: session.pagePolicy,
            contactEmail,
            contactLinkedin,
            contactPhone,
          },
          (msg) => setProgress(msg),
        );
        session.setGenerate(result);
        router.push("/review");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setLoading(false);
        setProgress(null);
      }
    },
    [router, session, contactEmail, contactLinkedin, contactPhone],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      const f = e.dataTransfer.files[0];
      if (f) startFlow(f, "");
    },
    [startFlow],
  );

  return (
    <>
      <div
        className={`drop ${drag ? "dragover" : ""}`}
        onDragEnter={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => !loading && fileRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.tex,.txt,.md"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) startFlow(f, "");
          }}
        />
        <div className="row between" style={{ gap: 18 }}>
          <div className="row" style={{ gap: 16 }}>
            <div className="drop-icon" aria-hidden>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M12 16V4M7 9l5-5 5 5M5 20h14" />
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 3 }}>
                {loading ? "Reading your résumé…" : "Drop your résumé here"}
              </div>
              <div className="font-mono" style={{ fontSize: 12, color: "var(--fg-4)" }}>
                {progress ?? "PDF · TEX · TXT — up to 10 MB"}
              </div>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-primary btn-lg"
            disabled={loading}
            onClick={(e) => {
              e.stopPropagation();
              fileRef.current?.click();
            }}
          >
            {loading ? "Working…" : "Choose file"}
          </button>
        </div>
        <div
          style={{
            borderTop: "1px solid var(--border)",
            marginTop: 18,
            paddingTop: 14,
            fontSize: 12,
            color: "var(--fg-4)",
          }}
          className="font-mono"
        >
          or{" "}
          <button
            type="button"
            className="nav-link"
            style={{ color: "var(--fg-2)", textDecoration: "underline", textUnderlineOffset: 3, padding: 0 }}
            onClick={(e) => {
              e.stopPropagation();
              setShowPaste((v) => !v);
            }}
          >
            paste plain text
          </button>
          {" · "}
          <span style={{ color: "var(--fg-5)" }}>sign in to save (soon)</span>
        </div>
      </div>

      {showPaste && (
        <div className="card fade-in" style={{ marginTop: 14 }}>
          <textarea
            value={paste}
            onChange={(e) => setPaste(e.target.value)}
            placeholder="Paste résumé plain text here…"
            rows={10}
            className="input"
            style={{ resize: "vertical", fontFamily: "inherit", lineHeight: 1.5 }}
          />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 10,
              marginTop: 10,
            }}
          >
            <input
              className="input"
              placeholder="Email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
            />
            <input
              className="input"
              placeholder="LinkedIn URL"
              value={contactLinkedin}
              onChange={(e) => setContactLinkedin(e.target.value)}
            />
            <input
              className="input"
              placeholder="Phone (optional)"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
            />
          </div>
          <div className="row between" style={{ marginTop: 12 }}>
            <span className="font-mono muted" style={{ fontSize: 11 }}>
              Contact fields override anything missing from the paste.
            </span>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={loading || !paste.trim()}
              onClick={() => startFlow(null, paste)}
            >
              {loading ? "Working…" : "Roast it →"}
            </button>
          </div>
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
    </>
  );
}
