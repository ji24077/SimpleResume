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

// --- ResumeScore Types ---

export type RubricScore = {
  score: number;
  reason: string;
  suggestion: string;
};

export type RepairReadiness = {
  recoverability: string;
  missing_dimensions: string[];
  ask_back_priority: string;
  revision_gain_potential: number;
};

export type BulletAnalysis = {
  id: string;
  role_id: string;
  text: string;
  composite_score: number;
  rubrics: Record<string, RubricScore>;
  tags: string[];
  strengths: string[];
  issues: string[];
  repair_readiness: RepairReadiness;
};

export type RoleAnalysis = {
  id: string;
  company: string;
  title: string;
  date_range: string;
  composite_score: number;
  rubrics: Record<string, RubricScore>;
  strengths: string[];
  issues: string[];
};

export type AtsAudit = {
  parseability: RubricScore;
  section_completeness: RubricScore;
  format_consistency: RubricScore;
  keyword_coverage: RubricScore;
  issues: string[];
};

export type Recommendation = {
  category: string;
  text: string;
  priority: string;
  expected_gain: number;
};

export type ResumeScoreResponse = {
  overall_score: number;
  grade: string;
  summary: string;
  top_strengths: string[];
  top_issues: string[];
  resume_rubrics: Record<string, RubricScore>;
  roles: RoleAnalysis[];
  bullets: BulletAnalysis[];
  ats_audit: AtsAudit;
  recommendations: Recommendation[];
};

// --- Resume Review Types (document-annotation UI) ---

export type IssueBBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type IssueLocation = {
  page: number;
  bbox: IssueBBox | null;
  section_id: string;
  bullet_id: string;
  line_hint: string;
};

export type IssueSeverity = "critical" | "moderate" | "minor";
export type IssueCategory = "ats" | "impact" | "clarity" | "formatting" | "credibility";

export type ReviewIssue = {
  id: string;
  title: string;
  severity: IssueSeverity;
  category: IssueCategory;
  description: string;
  location_label: string;
  location: IssueLocation;
  original_text: string;
  suggested_text: string;
  confidence: number;
};

export type CategoryScores = {
  ats: number;
  impact: number;
  clarity: number;
  formatting: number;
  credibility: number;
};

export type CredibilityInfo = {
  level: "high" | "medium" | "low";
  signals: string[];
};

export type ResumeBulletView = {
  id: string;
  text: string;
  issue_ids: string[];
};

export type ResumeRoleView = {
  id: string;
  company: string;
  title: string;
  date_range: string;
  bullets: ResumeBulletView[];
  issue_ids: string[];
};

export type ResumeSectionView = {
  id: string;
  type: "header" | "summary" | "education" | "experience" | "skills" | "projects" | "other";
  title: string;
  lines: string[];
  roles: ResumeRoleView[];
  issue_ids: string[];
};

export type ReviewResponse = {
  resume_id: string;
  overall_score: number;
  category_scores: CategoryScores;
  credibility: CredibilityInfo;
  issues: ReviewIssue[];
  sections: ResumeSectionView[];
};
