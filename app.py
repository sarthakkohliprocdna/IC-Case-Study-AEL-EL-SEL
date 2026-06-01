from __future__ import annotations

import pandas as pd
import streamlit as st

from src.evaluator import evaluate_response, ai_likeness_flags
from src.file_parser import read_uploaded_file
from src.question_generator import generate_questions, generate_role_questions
from src.utils import load_yaml, app_password, password_gate, recommendation_from_score, score_to_band
from src.workbook_evaluator import evaluate_candidate_workbook

try:
    from src.dynamic_question_generator import generate_dynamic_questions, openai_available
except Exception:
    generate_dynamic_questions = None

    def openai_available() -> bool:
        return False


st.set_page_config(page_title="IC Case Evaluator", page_icon="📊", layout="wide")

if not password_gate(st, app_password()):
    st.stop()

rubric = load_yaml("config/rubric.yaml")
questions = load_yaml("config/questions.yaml")

st.title("ONC-214 IC Case Evaluator")
st.caption("Evaluation-assist tool for IC design case submissions. Use as interviewer support, not as an automated hiring decision.")

with st.sidebar:
    st.header("Evaluator settings")
    candidate_name = st.text_input("Candidate name", placeholder="Optional")
    role_level = st.selectbox("Target role level", ["AEL", "EL", "SEL", "Unspecified"], index=0)

    st.markdown("---")
    use_dynamic_questions = st.checkbox(
        "Generate AI-assisted follow-up questions",
        value=False,
        help="Requires OPENAI_API_KEY in Render environment variables. Scores remain rule-based.",
    )

    if use_dynamic_questions and not openai_available():
        st.warning("OPENAI_API_KEY is not configured. The app will use rule-based questions only.")

    st.markdown("---")
    st.write("Upload narrative response and workbook separately.")
    uploaded_narrative = st.file_uploader(
        "Upload narrative / deck export",
        type=["txt", "csv", "xlsx", "xls", "docx", "pdf"],
        key="narrative",
    )
    uploaded_workbook = st.file_uploader(
        "Upload candidate workbook",
        type=["xlsx", "xls"],
        key="workbook",
    )

uploaded_text = ""
if uploaded_narrative:
    uploaded_text = read_uploaded_file(uploaded_narrative)

if "candidate_text" not in st.session_state:
    st.session_state.candidate_text = ""

if uploaded_text:
    st.session_state.candidate_text = uploaded_text

try:
    with open("sample_inputs/sample_candidate_response.txt", "r", encoding="utf-8") as f:
        sample = f.read()
except FileNotFoundError:
    sample = ""

if st.button("Load sample narrative response"):
    st.session_state.candidate_text = sample

text = st.text_area("Candidate narrative response text", value=st.session_state.candidate_text, height=260)

evaluate = st.button("Evaluate submission", type="primary")


def combined_score(narrative_score, workbook_score, role):
    if workbook_score is None:
        return narrative_score, "Narrative only"

    weights = {
        "AEL": (0.40, 0.60),
        "EL": (0.50, 0.50),
        "SEL": (0.70, 0.30),
        "Unspecified": (0.50, 0.50),
    }

    nw, ww = weights.get(role, (0.50, 0.50))
    return round(narrative_score * nw + workbook_score * ww, 1), f"Narrative {int(nw * 100)}% / Workbook {int(ww * 100)}%"


if evaluate:
    narrative_result = None
    workbook_result = None

    if text.strip():
        narrative_result = evaluate_response(text, rubric)

    if uploaded_workbook:
        try:
            workbook_result = evaluate_candidate_workbook(uploaded_workbook)
        except Exception as e:
            st.error(f"Workbook evaluation failed: {e}")

    if narrative_result is None and workbook_result is None:
        st.error("Please provide either a narrative response or a candidate workbook.")
        st.stop()

    narrative_score = narrative_result["overall_score"] if narrative_result else None
    workbook_score = workbook_result["overall_score"] if workbook_result else None

    if narrative_score is not None:
        combined, weighting_note = combined_score(narrative_score, workbook_score, role_level)
    else:
        combined, weighting_note = workbook_score, "Workbook only"

    st.markdown("## Overall evaluation")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Narrative score", "N/A" if narrative_score is None else f"{narrative_score}/100")
    c2.metric("Workbook score", "N/A" if workbook_score is None else f"{workbook_score}/100")
    c3.metric("Combined score", f"{combined}/100")
    c4.metric("Recommendation", recommendation_from_score(combined))
    st.caption(f"Combined score weighting: {weighting_note}")

    if narrative_result:
        st.markdown("## Narrative / presentation evaluation")
        st.info(narrative_result["summary"])

        rows = []
        for s in narrative_result["dimension_scores"]:
            rows.append(
                {
                    "Dimension": s.name,
                    "Weight": s.weight,
                    "Raw score": s.raw_score,
                    "Weighted score": s.weighted_score,
                    "Band": s.band,
                    "Commentary": s.commentary,
                }
            )

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with st.expander("Narrative evidence by dimension"):
            for s in narrative_result["dimension_scores"]:
                st.markdown(f"### {s.name} — {s.raw_score}/100 ({s.band})")
                st.write(s.commentary)
                st.markdown("**Matched positive signals**")
                st.write(", ".join(s.matched_positive) if s.matched_positive else "None detected")
                st.markdown("**Potential weak-signal matches**")
                st.write(", ".join(s.matched_weak) if s.matched_weak else "None detected")

        st.markdown("### AI-likeness / genericity flags")
        flags = ai_likeness_flags(text)
        if flags:
            for flag in flags:
                st.warning(flag)
        else:
            st.success("No major genericity flags detected. This does not prove the response was not AI-assisted.")

    if workbook_result:
        st.markdown("## Workbook / IC mechanics evaluation")

        wc_rows = []
        for k, v in workbook_result["component_scores"].items():
            wc_rows.append(
                {
                    "Component": k,
                    "Weight": workbook_result["weights"][k],
                    "Score": v,
                    "Band": score_to_band(v),
                }
            )

        st.dataframe(pd.DataFrame(wc_rows), use_container_width=True, hide_index=True)

        st.markdown("### Workbook diagnostics")
        for d in workbook_result["diagnostics"]:
            st.write(f"- {d}")

        with st.expander("Territory-level workbook evaluation"):
            display_df = workbook_result["evaluated_dataframe"].copy()
            display_df["Goal_Error_Pct"] = display_df["Goal_Error_Pct"].map(lambda x: f"{x:.1%}")
            display_df["Attainment"] = display_df["Attainment"].map(lambda x: f"{x:.1%}")
            display_df["Payout_Multiplier"] = display_df["Payout_Multiplier"].map(lambda x: f"{x:.2f}x")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        with st.expander("Candidate design inputs detected"):
            st.json(workbook_result["design_inputs"])

        if workbook_result.get("pay_curve") is not None:
            with st.expander("Candidate pay curve detected"):
                st.dataframe(workbook_result["pay_curve"], use_container_width=True, hide_index=True)
        else:
            st.caption("No Candidate_Pay_Curve sheet detected. Payout simulation used Threshold / Accelerator_Start / Cap from Candidate_Design.")

    if narrative_result:
        st.markdown("## Gap-based interviewer follow-up questions")
        st.caption("Generated from the candidate's weakest rubric dimensions.")
        followups = generate_questions(narrative_result["dimension_scores"], questions)
        for idx, q in enumerate(followups, start=1):
            st.write(f"{idx}. {q}")

    st.markdown("## AI-assisted dynamic follow-up questions")
    if use_dynamic_questions and openai_available() and generate_dynamic_questions:
        try:
            dynamic_output = generate_dynamic_questions(
                role_level=role_level,
                candidate_text=text,
                narrative_result=narrative_result,
                workbook_result=workbook_result,
            )
            st.markdown(dynamic_output)
        except Exception as e:
            st.warning(f"Dynamic question generation failed. Falling back to rule-based questions. Error: {e}")
    else:
        st.caption("Enable the sidebar toggle and configure OPENAI_API_KEY to generate candidate-specific dynamic questions.")

    st.markdown("## Role-calibrated discussion questions")
    role_questions = generate_role_questions(questions)
    tabs = st.tabs(["AEL", "EL", "SEL"])

    for tab, role in zip(tabs, ["AEL", "EL", "SEL"]):
        with tab:
            role_cfg = role_questions.get(role, {})
            st.markdown(f"**Focus:** {role_cfg.get('focus', '')}")
            for idx, q in enumerate(role_cfg.get("questions", []), start=1):
                st.write(f"{idx}. {q}")

    st.markdown("## Interviewer notes")
    st.text_area("Add notes from live discussion", height=160)

else:
    st.markdown("## How to use")
    st.write("Upload or paste the candidate narrative, upload the candidate workbook, then click **Evaluate submission**.")

    st.markdown("### Candidate workbook format")
    st.write("The workbook must contain `Candidate_Goals` and `Candidate_Design`. `Candidate_Pay_Curve` is optional but recommended for full pay curve evaluation.")
    st.dataframe(
        pd.DataFrame(
            [
                {"Sheet": "Candidate_Goals", "Required columns": "Territory_ID, Candidate_Q6_Goal", "Purpose": "Territory-level Q6 goal submission"},
                {"Sheet": "Candidate_Design", "Required columns": "Parameter, Value", "Purpose": "Plan design inputs and complexity indicators"},
                {"Sheet": "Candidate_Pay_Curve", "Required columns": "Attainment, Payout_Multiplier", "Purpose": "Optional. Used to evaluate the candidate's actual pay curve."},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## Rubric dimensions")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Dimension": d["name"],
                    "Weight": d["weight"],
                    "Description": d["description"],
                }
                for d in rubric.get("dimensions", [])
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
