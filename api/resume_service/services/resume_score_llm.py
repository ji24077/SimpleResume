"""LLM-based resume scoring using OpenAI."""

import json
import logging

from openai import OpenAI

from resume_service.config import settings
from resume_service.models.resume_score import ParsedResume

logger = logging.getLogger(__name__)

_RESUME_RUBRIC_NAMES = [
    "authenticity", "realism", "specificity", "clarity", "grammar", "relevance",
]
_ROLE_RUBRIC_NAMES = [
    "stack_completeness", "technical_depth", "impact_coverage",
    "ownership_profile", "role_relevance", "story_strength",
]
_BULLET_RUBRIC_NAMES = [
    "concision", "information_density", "technical_specificity",
    "impact_strength", "scope_clarity", "ownership_clarity",
    "readability", "role_relevance", "evidence_completeness",
    "claim_defensibility",
]


def _build_prompt(text: str, parsed: ParsedResume, job_description: str = "") -> str:
    roles_section = ""
    if parsed.roles:
        role_lines = []
        for r in parsed.roles:
            role_lines.append(f'  - id: "{r.id}", company: "{r.company}", title: "{r.title}"')
            for b in r.bullets[:8]:
                role_lines.append(f'    • {b}')
        roles_section = "\n".join(role_lines)

    jd_section = ""
    if job_description:
        jd_section = f"\n\n--- JOB DESCRIPTION ---\n{job_description[:3000]}\n--- END JOB DESCRIPTION ---"

    resume_rubrics_list = ", ".join(f'"{r}"' for r in _RESUME_RUBRIC_NAMES)
    role_rubrics_list = ", ".join(f'"{r}"' for r in _ROLE_RUBRIC_NAMES)
    bullet_rubrics_list = ", ".join(f'"{r}"' for r in _BULLET_RUBRIC_NAMES)

    return f"""You are an expert resume reviewer. Analyze the following resume and return a JSON object with detailed scoring.

--- RESUME TEXT ---
{text[:6000]}
--- END RESUME TEXT ---

--- PARSED ROLES ---
{roles_section}
--- END PARSED ROLES ---
{jd_section}

Return a JSON object with this exact structure:
{{
  "resume_rubrics": {{
    For each of [{resume_rubrics_list}]:
    "<rubric_name>": {{"score": <float 0-10>, "reason": "<1 sentence>", "suggestion": "<1 sentence or empty>"}}
  }},
  "roles": [
    For each role listed above:
    {{
      "id": "<role id from parsed roles>",
      "rubrics": {{
        For each of [{role_rubrics_list}]:
        "<rubric_name>": {{"score": <float 0-10>, "reason": "<1 sentence>", "suggestion": "<1 sentence or empty>"}}
      }},
      "strengths": ["<strength 1>", ...],
      "issues": ["<issue 1>", ...]
    }}
  ],
  "bullets": [
    For EVERY bullet point found in EVERY role (do NOT skip any bullet):
    {{
      "text": "<exact bullet text>",
      "role_id": "<role id this bullet belongs to>",
      "rubrics": {{
        For each of [{bullet_rubrics_list}]:
        "<rubric_name>": {{"score": <float 0-10>, "reason": "<1 sentence>", "suggestion": "<specific rewrite of this bullet or empty>"}}
      }},
      "strengths": ["<strength>", ...],
      "issues": ["<specific actionable issue>", ...],
      "rewrite": "<full improved version of this bullet with metrics, scope, and impact — or empty if bullet scores 8+>"
    }}
  ]
}}

Scoring guidelines:
- 9-10: Exceptional, publication-quality
- 7-8: Strong, minor improvements possible
- 5-6: Adequate but needs work
- 3-4: Weak, significant issues
- 1-2: Poor, major rewrite needed
- Be honest and specific. Focus on actionable feedback.
- Score relative to professional software engineering resumes.
- IMPORTANT: Include ALL bullets from ALL roles. Do NOT skip any.
- For each bullet's "rewrite" field: provide a concrete improved version (not a generic tip). Add specific metrics, technologies, scope, and outcomes. If the bullet is already strong (score 8+), leave "rewrite" empty.
{f'- Evaluate relevance against the provided job description.' if job_description else ''}"""


def llm_score_resume(text: str, parsed: ParsedResume, job_description: str = "") -> dict:
    """Score a resume using OpenAI. Returns empty dict on failure."""
    if not settings.openai_api_key:
        logger.info("No OpenAI API key configured; skipping LLM scoring.")
        return {}

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        prompt = _build_prompt(text, parsed, job_description)

        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are an expert resume analyst. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("LLM returned empty content.")
            return {}

        data = json.loads(content)
        result: dict = {}

        if "resume_rubrics" in data and isinstance(data["resume_rubrics"], dict):
            result["resume_rubrics"] = data["resume_rubrics"]
        if "roles" in data and isinstance(data["roles"], list):
            result["roles"] = data["roles"]
        if "bullets" in data and isinstance(data["bullets"], list):
            result["bullets"] = data["bullets"]

        return result

    except Exception:
        logger.exception("LLM scoring failed; falling back to rules-only.")
        return {}
