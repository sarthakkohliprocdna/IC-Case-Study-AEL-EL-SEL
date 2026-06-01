from __future__ import annotations
from typing import Dict, Any, List
from src.evaluator import DimensionScore

def generate_questions(scores: List[DimensionScore], question_config: Dict[str, Any], max_questions: int = 8) -> List[str]:
    bank = question_config.get("question_bank", {})
    sorted_scores = sorted(scores, key=lambda s: s.raw_score)
    questions = []
    for score in sorted_scores:
        for q in bank.get(score.name, []):
            if q not in questions:
                questions.append(q)
            if len(questions) >= max_questions:
                return questions
    return questions[:max_questions]

def generate_role_questions(question_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return question_config.get("role_question_bank", {})
