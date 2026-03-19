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

export type GenerateResponse = {
  latex_document: string;
  preview_sections: PreviewSection[];
  coaching: CoachingSection[];
};
