from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any
from src.utils import normalize_text, score_to_band, recommendation_from_score

@dataclass
class DimensionScore:
    name: str
    weight: float
    raw_score: float
    weighted_score: float
    band: str
    matched_positive: List[str]
    matched_weak: List[str]
    commentary: str

def keyword_hits(text: str, phrases: List[str]) -> List[str]:
    norm = normalize_text(text)
    return [phrase for phrase in phrases if normalize_text(phrase) in norm]

def evaluate_dimension(text: str, dimension: Dict[str, Any]) -> DimensionScore:
    positives = dimension.get("positive_signals", [])
    weak = dimension.get("weak_signals", [])
    positive_hits = keyword_hits(text, positives)
    weak_hits = keyword_hits(text, weak)
    positive_ratio = len(positive_hits) / max(len(positives), 1)
    weak_ratio = len(weak_hits) / max(len(weak), 1)
    raw = 35 + positive_ratio * 65 - weak_ratio * 20
    raw = max(0, min(100, raw))
    word_count = len((text or "").split())
    if word_count < 250:
        raw *= 0.75
    elif word_count < 500:
        raw *= 0.9
    weighted = raw * (dimension.get("weight", 0) / 100)
    band = score_to_band(raw)
    if raw >= 85:
        commentary = "Strong evidence of this capability."
    elif raw >= 70:
        commentary = "Good coverage with some room for deeper specificity."
    elif raw >= 55:
        commentary = "Partial coverage; follow-up probing recommended."
    else:
        commentary = "Limited evidence; significant probing required."
    return DimensionScore(dimension["name"], dimension.get("weight", 0), round(raw, 1), round(weighted, 1), band, positive_hits, weak_hits, commentary)

def evaluate_response(text: str, rubric: Dict[str, Any]) -> Dict[str, Any]:
    scores = [evaluate_dimension(text, d) for d in rubric.get("dimensions", [])]
    total = round(sum(s.weighted_score for s in scores), 1)
    return {
        "overall_score": total,
        "overall_band": score_to_band(total),
        "recommendation": recommendation_from_score(total),
        "dimension_scores": scores,
        "summary": build_summary(total, scores),
    }

def build_summary(total: float, scores: List[DimensionScore]) -> str:
    sorted_scores = sorted(scores, key=lambda s: s.raw_score, reverse=True)
    strengths = [s.name for s in sorted_scores[:2]]
    gaps = [s.name for s in sorted_scores[-2:]]
    return f"Overall score: {total}. Strongest areas: {', '.join(strengths)}. Areas to probe further: {', '.join(gaps)}."

def ai_likeness_flags(text: str) -> List[str]:
    flags = []
    lower = normalize_text(text)
    words = text.split()
    generic_phrases = ["it is important to note", "in conclusion", "there are several factors", "best practice", "holistic approach", "leverage synergies", "robust framework"]
    case_specific_terms = ["onc-214", "rare oncology", "nbrx", "territory", "access", "pull-through", "pay curve", "attainment"]
    generic_count = sum(1 for p in generic_phrases if p in lower)
    case_count = sum(1 for p in case_specific_terms if normalize_text(p) in lower)
    if generic_count >= 2 and case_count <= 2:
        flags.append("Response uses generic business language with limited case-specific anchoring.")
    if len(words) > 900 and case_count <= 3:
        flags.append("Long response with low reference to case-specific concepts.")
    if "assumption" not in lower and "tradeoff" not in lower and "trade off" not in lower:
        flags.append("Response does not clearly state assumptions or tradeoffs.")
    if "q6" not in lower and "quarter 6" not in lower:
        flags.append("No explicit reflection on Quarter 6 outcomes detected.")
    return flags
