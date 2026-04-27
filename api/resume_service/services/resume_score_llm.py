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


def _build_bullets_only_prompt(text: str, parsed: ParsedResume) -> str:
    """Focused fallback prompt: ask for bullets only.

    GPT-4o sometimes emits resume_rubrics + roles but truncates / omits the
    bullets array. We retry with a stripped-down prompt that asks for nothing
    else, so the model stays inside its budget for the bullet section.
    """
    role_lines = []
    for r in parsed.roles:
        role_lines.append(f'  - id: "{r.id}", company: "{r.company}", title: "{r.title}"')
        for b in r.bullets[:10]:
            role_lines.append(f"    • {b}")
    bullet_rubrics_list = ", ".join(f'"{r}"' for r in _BULLET_RUBRIC_NAMES)

    return f"""Return ONLY a JSON object with one key: "bullets". For EVERY bullet point in EVERY role below, return one entry. Do NOT skip any bullet.

--- ROLES ---
{chr(10).join(role_lines)}
--- END ROLES ---

Output shape:
{{
  "bullets": [
    {{
      "text": "<exact bullet text>",
      "role_id": "<role id>",
      "rubrics": {{ "<name>": {{"score": <0-10>, "reason": "<1 sentence>", "suggestion": "<rewrite or empty>"}} }},
      "strengths": ["<...>"],
      "issues": ["<...>"],
      "rewrite": "<full improved bullet with metrics, scope, impact — empty if score>=8>"
    }}
  ]
}}

Rubric names: [{bullet_rubrics_list}]

Source text (for context):
{text[:4000]}
"""


def _retry_bullets(client: "OpenAI", text: str, parsed: ParsedResume) -> list:
    """One-shot retry that asks only for the bullets array."""
    try:
        prompt = _build_bullets_only_prompt(text, parsed)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume analyst. Return only valid JSON. Do not skip bullets.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=8000,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        bullets = data.get("bullets")
        return bullets if isinstance(bullets, list) else []
    except Exception:
        logger.exception("Bullets-only retry failed.")
        return []


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
            max_tokens=8000,
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

        n_bullets = len(result.get("bullets") or [])
        expected = sum(len(r.bullets) for r in parsed.roles) if parsed and parsed.roles else 0
        # Threshold: when far below expected (or zero), retry with the
        # bullets-only focused prompt.
        if expected > 0 and n_bullets < max(2, expected // 2 + 1):
            logger.warning(
                "llm_score_resume sparse response: keys=%s bullets=%d expected=%d — retrying with bullets-only prompt",
                sorted(data.keys()),
                n_bullets,
                expected,
            )
            recovered = _retry_bullets(client, text, parsed)
            if recovered:
                # Merge — prefer recovered list if it's larger.
                if len(recovered) > n_bullets:
                    result["bullets"] = recovered
                    logger.info(
                        "llm_score_resume recovered %d bullets via retry (was %d)",
                        len(recovered),
                        n_bullets,
                    )

        return result

    except Exception:
        logger.exception("LLM scoring failed; falling back to rules-only.")
        return {}
