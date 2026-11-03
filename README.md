# Agentic AI Mortgage Intake Assistant — Educational Starter

A small Python/SQLite intake-completeness prototype using **synthetic borrower data only**. It does not assess creditworthiness or decide mortgage eligibility. The first version is **not an autonomous agent**; it is a deterministic workflow with optional LLM-assisted summarization and mandatory human administrative review.

## Prerequisites

Python 3.10+. SQLite is included with Python. Optional: `pip install openai` for AI-generated summaries (may incur API charges).

## Run

From this directory:

```bash
python app.py import
python app.py list
python app.py show APP-1002
python app.py review APP-1002 --reviewer "Demo Loan Officer" --note "Verified missing items and requested follow-up"
python app.py show APP-1002
python -m unittest discover -s tests -v
```

## Enable optional LLM summarization

1. Install the official Python SDK: `python -m pip install openai`
2. Set `OPENAI_API_KEY` in your terminal environment. Do NOT commit it to GitHub.
3. Run `python app.py import --ai` to regenerate summaries. Re-import resets reviews.
4. To use another available model, set `OPENAI_MODEL`.

Do not send real personal mortgage or financial records to the API without appropriate authorization, legal compliance, retention controls, and security review.

## Architecture

`data/applications.json` → `validate()` in Python → `applications` table in SQLite → optional LLM summary → manual reviewer sign-off.

* Validation rules are deterministic, not produced by an LLM.
* The LLM receives only the application ID and validation findings, not sensitive applicant details.
* SQLite writes use SQL parameters to avoid injection.
* All applicants, incomes, and loan values are fabricated.
* A review sign-off means intake completeness review only; not loan approval.

## Example SQL

```sql
SELECT status, COUNT(*) AS applications
FROM applications
GROUP BY status;
```

## Next extensions

Implement a restricted tool-using agent to choose between reviewing missing-document lists and retrieving application details, audit every tool call, add a real reviewer UI, and add stronger validation, role-based access, logging, and controlled document parsing. The current demo does not provide production-grade data security or regulatory compliance.
