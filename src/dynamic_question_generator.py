from __future__ import annotations

import os
from typing import Any, Dict, Optional

from openai import OpenAI

from src.utils import load_yaml


def ai_available() -> bool:
    provider = os.environ.get("AI_PROVIDER", "groq").lower()

    if provider == "groq":
        return bool(os.environ.get("GROQ_API_KEY"))

    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))

    return bool(os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def get_ai_client() -> OpenAI:
    provider = os.environ.get("AI_PROVIDER", "groq").lower()

    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        return OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        return OpenAI(api_key=api_key)

    # Auto fallback: prefer Groq, then OpenAI
    if os.environ.get("GROQ_API_KEY"):
        return OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )

    if os.environ.get("OPENAI_API_KEY"):
        return OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    raise RuntimeError("No AI provider key is configured.")


def get_model_name() -> str:
    provider = os.environ.get("AI_PROVIDER", "groq").lower()

    if provider == "groq":
        return os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    if provider == "openai":
        return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if os.environ.get("GROQ_API_KEY"):
        return os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def build_workbook_summary(workbook_result: Optional[Dict[str, Any]]) -> str:
    if not workbook_result:
        return "No workbook evaluation was available."

    component_scores = workbook_result.get("component_scores", {})
    diagnostics = workbook_result.get("diagnostics", [])

    lines = [
        f"Workbook score: {workbook_result.get('overall_score', 'N/A')}/100",
        "Component scores:",
    ]

    for component, score in component_scores.items():
        lines.append(f"- {component}: {score}")

    if diagnostics:
        lines.append("Diagnostics:")
        for item in diagnostics:
            lines.append(f"- {item}")

    return "\n".join(lines)


def build_narrative_summary(narrative_result: Optional[Dict[str, Any]]) -> str:
    if not narrative_result:
        return "No narrative evaluation was available."

    lines = [
        f"Narrative score: {narrative_result.get('overall_score', 'N/A')}/100",
        narrative_result.get("summary", ""),
        "Dimension scores:",
    ]

    for score in narrative_result.get("dimension_scores", []):
        lines.append(
            f"- {score.name}: {score.raw_score}/100; positives={score.matched_positive}; weak_signals={score.matched_weak}"
        )

    return "\n".join(lines)


def generate_dynamic_questions(
    *,
    role_level: str,
    candidate_text: str,
    narrative_result: Optional[Dict[str, Any]],
    workbook_result: Optional[Dict[str, Any]],
    prompt_config_path: str = "config/llm_prompts.yaml",
    model: Optional[str] = None,
) -> str:
    """
    Generate AI-assisted interviewer follow-up questions.

    This function is intentionally used only for question generation.
    It does not alter scores or recommendations.
    """
    if not ai_available():
        raise RuntimeError("No AI provider key is configured.")

    prompts = load_yaml(prompt_config_path)["dynamic_question_generation"]

    candidate_excerpt = (candidate_text or "").strip()
    if len(candidate_excerpt) > 5000:
        candidate_excerpt = candidate_excerpt[:5000] + "\n...[truncated]"

    user_prompt = prompts["user_prompt_template"].format(
        role_level=role_level,
        narrative_summary=build_narrative_summary(narrative_result),
        workbook_summary=build_workbook_summary(workbook_result),
        candidate_excerpt=candidate_excerpt or "No candidate narrative text was provided.",
    )

    client = get_ai_client()
    response = client.chat.completions.create(
        model=model or get_model_name(),
        temperature=0.25,
        messages=[
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content or ""
