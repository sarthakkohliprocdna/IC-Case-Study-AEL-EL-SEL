# IC Case Evaluator V2

A Streamlit evaluation-assist app for the ONC-214 Incentive Compensation case study.

## What V2 evaluates

### 1. Narrative / presentation response
- Problem structuring
- IC design logic
- Commercial understanding
- Operationalization
- Q6 adaptability
- Executive communication

### 2. Candidate workbook
The workbook evaluator expects a candidate Excel file with two sheets:

#### Sheet: `Candidate_Goals`
Required columns:
- `Territory_ID`
- `Candidate_Q6_Goal`

#### Sheet: `Candidate_Design`
Required columns:
- `Parameter`
- `Value`

Recommended parameters:
- `Goal_Structure`
- `Primary_Metric`
- `Secondary_Metric`
- `Access_Metric`
- `Threshold`
- `Accelerator_Start`
- `Cap`
- `Metric_Count`
- `Modifier_Count`
- `Exception_Rules`

The app compares submitted goals against the hidden reference file:
`config/hidden_q6_reference.csv`

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Render deployment

1. Upload this folder to GitHub.
2. In Render, create a new Blueprint.
3. Select this GitHub repo.
4. Add environment variable:
   - `APP_PASSWORD`: choose a password.
5. Deploy.

## Notes

This is an evaluation-assist tool, not an automated hiring decision system. Human interviewers should review outputs and apply judgment.

## Candidate workbook format

The workbook evaluator expects:

### Required sheet: `Candidate_Goals`
Required columns:
- `Territory_ID`
- `Candidate_Q6_Goal`

### Required sheet: `Candidate_Design`
Required columns:
- `Parameter`
- `Value`

Recommended parameters:
- `Goal_Structure`
- `Primary_Metric`
- `Secondary_Metric`
- `Access_Metric`
- `Threshold`
- `Accelerator_Start`
- `Cap`
- `Metric_Count`
- `Modifier_Count`
- `Exception_Rules`

### Optional but recommended sheet: `Candidate_Pay_Curve`
Required columns if included:
- `Attainment`
- `Payout_Multiplier`

If `Candidate_Pay_Curve` is present, the evaluator interpolates the candidate's submitted curve to simulate payouts. If it is absent, the evaluator uses a default curve based on `Threshold`, `Accelerator_Start`, and `Cap` from `Candidate_Design`.

## Important evaluator behavior

- Narrative scoring uses rubric signals and expanded synonym groups.
- Workbook scoring compares candidate Q6 goals against the hidden Q6 reference file.
- Candidate workbooks with missing or extra territories are rejected to avoid silent mismatches.
- AI-assisted dynamic questions are optional and require `OPENAI_API_KEY`; AI does not change the score.
