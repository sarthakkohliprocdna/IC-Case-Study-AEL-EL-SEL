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
