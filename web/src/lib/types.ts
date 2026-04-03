export type PreviewSection = {
  kind: string;
  title: string;
  subtitle: string | null;
  bullets: string[];
};

export type CoachingItem = {
  why_better: string;
};

export type CoachingSection = {
  section_why: string;
  items: CoachingItem[];
};

export type PagePolicy = "strict_one_page" | "allow_multi";

export type GenerateResponse = {
  latex_document: string;
  preview_sections: PreviewSection[];
  coaching: CoachingSection[];
  /** Server compile page count; omitted if check skipped or compile failed */
  pdf_page_count?: number | null;
  /** True if multi-page output was revised down to one page */
  one_page_enforced?: boolean;
  page_policy_applied?: PagePolicy;
  revision_log?: string[];
  revision_log_ko?: string[];
  /** Heuristic: large bottom whitespace on 1-page PDF; null if not checked */
  pdf_layout_underfull?: boolean | null;
  /** LLM rounds used to densify after layout check */
  density_expand_rounds?: number;
  /** ATS smoke-test issue code if any; omitted when passed */
  ats_issue_code?: string | null;
  /** Checker LLM diagnostic issues (RESUME_QUALITY_CHECKER=1) */
  quality_issues?: Array<Record<string, unknown>> | null;
};
