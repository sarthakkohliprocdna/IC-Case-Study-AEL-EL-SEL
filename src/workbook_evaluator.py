from __future__ import annotations
from io import BytesIO
from typing import Dict, Any, Tuple, List
import numpy as np
import pandas as pd
from src.utils import score_to_band

REQUIRED_GOAL_COLUMNS = {"Territory_ID", "Candidate_Q6_Goal"}
REQUIRED_DESIGN_COLUMNS = {"Parameter", "Value"}

def read_candidate_workbook(uploaded_file) -> Tuple[pd.DataFrame, pd.DataFrame]:
    data = uploaded_file.read()
    xl = pd.ExcelFile(BytesIO(data))
    sheets_lower = {s.lower(): s for s in xl.sheet_names}

    goals_sheet = sheets_lower.get("candidate_goals")
    design_sheet = sheets_lower.get("candidate_design")

    if not goals_sheet:
        raise ValueError("Candidate workbook must include a sheet named 'Candidate_Goals'.")
    if not design_sheet:
        raise ValueError("Candidate workbook must include a sheet named 'Candidate_Design'.")

    goals = xl.parse(goals_sheet)
    design = xl.parse(design_sheet)

    missing_goals = REQUIRED_GOAL_COLUMNS - set(goals.columns)
    missing_design = REQUIRED_DESIGN_COLUMNS - set(design.columns)

    if missing_goals:
        raise ValueError(f"Candidate_Goals is missing required columns: {sorted(missing_goals)}")
    if missing_design:
        raise ValueError(f"Candidate_Design is missing required columns: {sorted(missing_design)}")

    goals["Territory_ID"] = goals["Territory_ID"].astype(str).str.strip()
    goals["Candidate_Q6_Goal"] = pd.to_numeric(goals["Candidate_Q6_Goal"], errors="coerce")
    return goals, design

def design_to_dict(design: pd.DataFrame) -> Dict[str, str]:
    out = {}
    for _, row in design.iterrows():
        key = str(row.get("Parameter", "")).strip()
        val = str(row.get("Value", "")).strip()
        if key:
            out[key] = val
    return out

def payout_multiplier(attainment: float, threshold: float = 0.80, accelerator_start: float = 1.10, cap: float = 1.50) -> float:
    if np.isnan(attainment):
        return np.nan
    if attainment < threshold:
        return 0.0
    if attainment < 1.0:
        return 0.5 + (attainment - threshold) / (1.0 - threshold) * 0.5
    if attainment < accelerator_start:
        return 1.0 + (attainment - 1.0) / (accelerator_start - 1.0) * 0.25
    if attainment < 1.2:
        return 1.25 + (attainment - accelerator_start) / (1.2 - accelerator_start) * 0.20
    return min(cap, 1.45 + max(0, attainment - 1.2) * 0.5)

def safe_float(value, default):
    try:
        if value is None:
            return default
        s = str(value).replace("%", "").strip()
        f = float(s)
        if f > 5:
            f = f / 100
        return f
    except Exception:
        return default

def evaluate_candidate_workbook(uploaded_file, reference_path: str = "config/hidden_q6_reference.csv") -> Dict[str, Any]:
    goals, design = read_candidate_workbook(uploaded_file)
    design_map = design_to_dict(design)
    ref = pd.read_csv(reference_path)
    ref["Territory_ID"] = ref["Territory_ID"].astype(str).str.strip()

    df = ref.merge(goals, on="Territory_ID", how="left")
    if df["Candidate_Q6_Goal"].isna().any():
        missing = df.loc[df["Candidate_Q6_Goal"].isna(), "Territory_ID"].tolist()
        raise ValueError(f"Missing Q6 goals for territories: {missing[:10]}")

    df["Goal_Error_Pct"] = (df["Candidate_Q6_Goal"] - df["Q6_Actual_NBRx"]).abs() / df["Q6_Actual_NBRx"].replace(0, np.nan)
    df["Attainment"] = df["Q6_Actual_NBRx"] / df["Candidate_Q6_Goal"].replace(0, np.nan)

    threshold = safe_float(design_map.get("Threshold"), 0.80)
    accelerator_start = safe_float(design_map.get("Accelerator_Start"), 1.10)
    cap = safe_float(design_map.get("Cap"), 1.50)

    df["Payout_Multiplier"] = df["Attainment"].apply(lambda x: payout_multiplier(x, threshold, accelerator_start, cap))

    goal_accuracy = score_goal_accuracy(df)
    distribution = score_attainment_distribution(df, threshold)
    fairness = score_fairness(df)
    payout = score_payout_design(df)
    complexity = score_complexity(design_map)
    commercial = score_commercial_alignment(design_map)

    component_scores = {
        "Goal setting accuracy": goal_accuracy,
        "Attainment distribution health": distribution,
        "Territory fairness": fairness,
        "Payout design quality": payout,
        "Operational complexity": complexity,
        "Commercial alignment": commercial,
    }

    weights = {
        "Goal setting accuracy": 25,
        "Attainment distribution health": 20,
        "Territory fairness": 15,
        "Payout design quality": 15,
        "Operational complexity": 10,
        "Commercial alignment": 15,
    }

    overall = round(sum(component_scores[k] * weights[k] / 100 for k in component_scores), 1)

    return {
        "overall_score": overall,
        "overall_band": score_to_band(overall),
        "component_scores": component_scores,
        "weights": weights,
        "diagnostics": build_diagnostics(df, design_map),
        "evaluated_dataframe": df,
        "design_inputs": design_map,
    }

def score_goal_accuracy(df: pd.DataFrame) -> float:
    mean_error = df["Goal_Error_Pct"].mean()
    if mean_error <= 0.05:
        return 100
    if mean_error <= 0.10:
        return 85
    if mean_error <= 0.15:
        return 70
    if mean_error <= 0.20:
        return 50
    return 25

def score_attainment_distribution(df: pd.DataFrame, threshold: float) -> float:
    below_threshold = (df["Attainment"] < threshold).mean()
    above_120 = (df["Attainment"] > 1.20).mean()
    near_goal = ((df["Attainment"] >= 0.90) & (df["Attainment"] <= 1.10)).mean()

    score = 100
    if below_threshold > 0.30:
        score -= 25
    elif below_threshold > 0.20:
        score -= 10
    if above_120 > 0.25:
        score -= 20
    elif above_120 > 0.15:
        score -= 10
    if near_goal < 0.35:
        score -= 15
    if near_goal > 0.80:
        score -= 10
    return max(0, round(score, 1))

def score_fairness(df: pd.DataFrame) -> float:
    # Good designs should generally align goals with opportunity but not perfectly ignore recent performance.
    corr = df["Candidate_Q6_Goal"].corr(df["Opportunity_Index"])
    if pd.isna(corr):
        return 40
    score = 55 + min(max(corr, 0), 1) * 45
    # Penalize if low opportunity territories have extreme stretch vs actual.
    low_opp = df[df["Opportunity_Index"] <= df["Opportunity_Index"].quantile(0.25)]
    if not low_opp.empty and (low_opp["Attainment"] < 0.75).mean() > 0.30:
        score -= 15
    return max(0, min(100, round(score, 1)))

def score_payout_design(df: pd.DataFrame) -> float:
    payouts = df["Payout_Multiplier"].fillna(0)
    total = payouts.sum()
    if total <= 0:
        return 20
    top_10_count = max(1, int(np.ceil(len(payouts) * 0.10)))
    top_share = payouts.sort_values(ascending=False).head(top_10_count).sum() / total
    cv = payouts.std() / payouts.mean() if payouts.mean() else 1

    score = 100
    if top_share > 0.35:
        score -= 25
    elif top_share > 0.25:
        score -= 10
    if cv > 0.75:
        score -= 20
    elif cv > 0.50:
        score -= 10
    if payouts.max() > 1.7:
        score -= 15
    return max(0, round(score, 1))

def score_complexity(design_map: Dict[str, str]) -> float:
    metric_count = safe_float(design_map.get("Metric_Count"), 2)
    modifier_count = safe_float(design_map.get("Modifier_Count"), 1)
    exception_rules = safe_float(design_map.get("Exception_Rules"), 1)

    score = 100
    if metric_count > 4:
        score -= 20
    if metric_count > 6:
        score -= 20
    if modifier_count > 2:
        score -= 15
    if exception_rules > 3:
        score -= 20
    return max(0, round(score, 1))

def score_commercial_alignment(design_map: Dict[str, str]) -> float:
    text = " ".join(str(v).lower() for v in design_map.values())
    score = 45
    if "nbrx" in text:
        score += 15
    if "new writer" in text or "new prescriber" in text or "hcp" in text:
        score += 15
    if "access" in text or "pull" in text:
        score += 15
    if "trx" in text or "persistence" in text or "sustained" in text:
        score += 10
    if "100% nbrx" in text or "only nbrx" in text:
        score -= 20
    return max(0, min(100, round(score, 1)))

def build_diagnostics(df: pd.DataFrame, design_map: Dict[str, str]) -> List[str]:
    diagnostics = []
    diagnostics.append(f"Mean absolute goal error: {df['Goal_Error_Pct'].mean():.1%}.")
    diagnostics.append(f"Median attainment: {df['Attainment'].median():.1%}.")
    diagnostics.append(f"Territories below threshold: {(df['Attainment'] < safe_float(design_map.get('Threshold'), 0.80)).mean():.1%}.")
    diagnostics.append(f"Territories above 120% attainment: {(df['Attainment'] > 1.20).mean():.1%}.")
    payouts = df["Payout_Multiplier"].fillna(0)
    top_10_count = max(1, int(np.ceil(len(payouts) * 0.10)))
    top_share = payouts.sort_values(ascending=False).head(top_10_count).sum() / payouts.sum() if payouts.sum() else 0
    diagnostics.append(f"Top 10% payout concentration: {top_share:.1%}.")
    return diagnostics
