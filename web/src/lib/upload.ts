import type {
  BulletChatMessage,
  BulletChatResult,
  GenerateResponse,
  PagePolicy,
  ParseResponse,
} from "@/lib/types";

export type ProgressHandler = (message: string | null) => void;

/** Generic NDJSON stream reader. Yields progress events and returns the final `result.data`. */
export async function readNdjsonResult<T>(
  res: Response,
  onProgress?: ProgressHandler,
): Promise<T> {
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(
      typeof json.detail === "string"
        ? json.detail
        : JSON.stringify(json.detail || json) || res.statusText,
    );
  }
  if (!res.body) throw new Error("Empty response from server");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: T | null = null;

  const consumeLine = (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    let ev: {
      type?: string;
      message?: string;
      message_en?: string;
      data?: T;
      detail?: string;
    };
    try {
      ev = JSON.parse(trimmed) as typeof ev;
    } catch {
      return;
    }
    if (ev.type === "progress") {
      onProgress?.(ev.message ?? ev.message_en ?? null);
    } else if (ev.type === "result" && ev.data !== undefined) {
      finalResult = ev.data as T;
    } else if (ev.type === "error") {
      throw new Error(ev.detail ?? "Stream failed");
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) consumeLine(line);
  }
  if (buffer.trim()) consumeLine(buffer);

  if (!finalResult) throw new Error("No result from stream");
  return finalResult;
}

export async function readStreamResult(
  res: Response,
  onProgress?: ProgressHandler,
): Promise<GenerateResponse> {
  return readNdjsonResult<GenerateResponse>(res, onProgress);
}

export type BulletChatRequest = {
  issueId: string;
  originalText: string;
  /** Reviewer-vetted starting suggestion (issue.suggested_text). Frozen across turns. */
  baselineSuggestion: string;
  /** Mutating UI-side suggestion. Sent for backward compat; server prefers baselineSuggestion. */
  currentSuggestion: string;
  userMessage: string;
  history: BulletChatMessage[];
  sectionId?: string;
  bulletId?: string;
  severity?: string;
  category?: string;
};

export async function submitBulletChat(
  req: BulletChatRequest,
  onProgress?: ProgressHandler,
): Promise<BulletChatResult> {
  const res = await fetch("/api/bullet-chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      issue_id: req.issueId,
      original_text: req.originalText,
      baseline_suggestion: req.baselineSuggestion,
      current_suggestion: req.currentSuggestion,
      user_message: req.userMessage,
      history: req.history,
      section_id: req.sectionId ?? null,
      bullet_id: req.bulletId ?? null,
      severity: req.severity ?? null,
      category: req.category ?? null,
    }),
  });
  return readNdjsonResult<BulletChatResult>(res, onProgress);
}

export type ContactFields = {
  contactEmail?: string;
  contactLinkedin?: string;
  contactPhone?: string;
};

export type SubmitInput = ContactFields & {
  file: File | null;
  paste: string;
};

export async function submitParse(input: SubmitInput): Promise<ParseResponse> {
  const { file, paste, contactEmail = "", contactLinkedin = "", contactPhone = "" } = input;
  let res: Response;
  if (file) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("contact_email", contactEmail);
    fd.append("contact_linkedin", contactLinkedin);
    fd.append("contact_phone", contactPhone);
    res = await fetch("/api/parse", { method: "POST", body: fd });
  } else {
    res = await fetch("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: paste,
        contact_email: contactEmail,
        contact_linkedin: contactLinkedin,
        contact_phone: contactPhone,
      }),
    });
  }
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(
      typeof json.detail === "string"
        ? json.detail
        : JSON.stringify(json.detail || json) || res.statusText,
    );
  }
  return (await res.json()) as ParseResponse;
}

export type LegacyGenerateInput = SubmitInput & { pagePolicy: PagePolicy };

export async function submitLegacyGenerate(
  input: LegacyGenerateInput,
  onProgress?: ProgressHandler,
): Promise<GenerateResponse> {
  const { file, paste, pagePolicy, contactEmail = "", contactLinkedin = "", contactPhone = "" } = input;
  let res: Response;
  if (file) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("page_policy", pagePolicy);
    fd.append("contact_email", contactEmail);
    fd.append("contact_linkedin", contactLinkedin);
    fd.append("contact_phone", contactPhone);
    res = await fetch("/api/generate-stream", { method: "POST", body: fd });
  } else {
    res = await fetch("/api/generate-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: paste,
        page_policy: pagePolicy,
        contact_email: contactEmail,
        contact_linkedin: contactLinkedin,
        contact_phone: contactPhone,
      }),
    });
  }
  return readStreamResult(res, onProgress);
}

export async function submitStructuredGenerate(
  resumeData: import("@/lib/types").ResumeData,
  pagePolicy: PagePolicy,
  onProgress?: ProgressHandler,
): Promise<GenerateResponse> {
  const res = await fetch("/api/generate-structured", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume_data: resumeData, page_policy: pagePolicy }),
  });
  return readStreamResult(res, onProgress);
}

const LOOKS_LIKE_EMAIL = /\S+@\S+\.\S+/;
const HAS_LINKEDIN = /linkedin\.com/i;

export function pasteContactGaps(paste: string) {
  const p = paste.trim();
  if (!p) return { needEmail: false, needLinkedin: false };
  return {
    needEmail: !LOOKS_LIKE_EMAIL.test(p),
    needLinkedin: !HAS_LINKEDIN.test(p),
  };
}

export function downloadTex(latex: string, filename = "resume.tex") {
  const blob = new Blob([latex], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export function downloadPdfBlob(blob: Blob, filename = "resume.pdf") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
