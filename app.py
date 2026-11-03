"""Educational mortgage intake demo. Synthetic data only; not a lending decision system."""
import argparse
import json
import os
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "mortgage_intake.db"
REQUIRED_DOCS = {"photo_id", "pay_stub", "bank_statement", "tax_return"}


def validate(app):
    """Apply deterministic intake completeness rules, not credit eligibility rules."""
    missing_docs = sorted(REQUIRED_DOCS - set(app.get("documents", [])))
    missing_fields = [key for key in ("applicant", "annual_income", "loan_amount") if app.get(key) is None or app.get(key) == ""]
    return {"missing_documents": missing_docs, "missing_fields": missing_fields,
            "status": "needs_review" if missing_docs or missing_fields else "ready_for_human_review"}


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS applications (
        application_id TEXT PRIMARY KEY,
        applicant TEXT NOT NULL,
        input_json TEXT NOT NULL,
        missing_documents TEXT NOT NULL,
        missing_fields TEXT NOT NULL,
        status TEXT NOT NULL,
        summary TEXT NOT NULL,
        reviewer TEXT,
        review_note TEXT
    )""")
    con.commit()
    return con


def basic_summary(app, checks):
    docs = ", ".join(checks["missing_documents"]) or "none"
    fields = ", ".join(checks["missing_fields"]) or "none"
    return (f"Intake summary for {app['application_id']}: missing documents: {docs}; "
            f"missing fields: {fields}. Status: {checks['status']}. "
            "A human must verify source information and decide administrative next steps; "
            "this is not a loan approval recommendation.")


def ai_summary(app, checks):
    """Optional LLM-assisted summary; returns to deterministic fallback if no key is set."""
    if not os.getenv("OPENAI_API_KEY"):
        return basic_summary(app, checks)
    try:
        from openai import OpenAI
        client = OpenAI()
        # Provide only synthetic examples in this demonstration.
        payload = {"application_id": app["application_id"], "validation": checks}
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.5"),
            instructions=("You summarize synthetic mortgage intake completeness findings. "
                          "Use only the provided JSON. Do not invent facts, assess creditworthiness, "
                          "recommend approval or denial, or change deterministic validation results. "
                          "Write three short sentences, including a human-review reminder."),
            input=json.dumps(payload),
        )
        return response.output_text or basic_summary(app, checks)
    except Exception as exc:
        print(f"AI unavailable ({type(exc).__name__}); using deterministic summary.")
        return basic_summary(app, checks)


def import_data(use_ai=False):
    apps = json.loads((BASE / "data" / "applications.json").read_text(encoding="utf-8"))
    with connect() as con:
        for app in apps:
            checks = validate(app)
            summary = ai_summary(app, checks) if use_ai else basic_summary(app, checks)
            con.execute("""INSERT INTO applications
                (application_id, applicant, input_json, missing_documents, missing_fields, status, summary, reviewer, review_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                ON CONFLICT(application_id) DO UPDATE SET
                applicant=excluded.applicant, input_json=excluded.input_json,
                missing_documents=excluded.missing_documents, missing_fields=excluded.missing_fields,
                status=excluded.status, summary=excluded.summary,
                reviewer=NULL, review_note=NULL""",
                (app["application_id"], app["applicant"], json.dumps(app),
                 json.dumps(checks["missing_documents"]), json.dumps(checks["missing_fields"]),
                 checks["status"], summary))
    print(f"Imported {len(apps)} synthetic applications. (Import resets previous review sign-offs.)")


def list_records():
    with connect() as con:
        for row in con.execute("SELECT application_id, applicant, status, reviewer FROM applications ORDER BY application_id"):
            print(f"{row['application_id']} | {row['applicant']} | {row['status']} | reviewer: {row['reviewer'] or 'pending'}")


def show(application_id):
    with connect() as con:
        row = con.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
        if row is None:
            print("No application with that ID")
            return
        print(row["summary"])
        print("Source:", row["input_json"])
        print("Reviewer:", row["reviewer"] or "pending")
        print("Review note:", row["review_note"] or "none")


def review(application_id, reviewer, note):
    if not reviewer.strip() or not note.strip():
        raise ValueError("Reviewer and note must not be empty")
    with connect() as con:
        cur = con.execute("""UPDATE applications
            SET reviewer = ?, review_note = ?, status = 'intake_reviewed'
            WHERE application_id = ?""", (reviewer, note, application_id))
        if cur.rowcount == 0:
            print("No application with that ID")
            return
    print("Administrative intake review recorded; this is NOT a loan decision.")


def main():
    parser = argparse.ArgumentParser(description="Synthetic mortgage intake demo")
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="Load synthetic applications")
    imp.add_argument("--ai", action="store_true", help="Use LLM for summaries if OPENAI_API_KEY is configured")
    sub.add_parser("list", help="List stored applications")
    s = sub.add_parser("show", help="Show one application's findings")
    s.add_argument("id")
    r = sub.add_parser("review", help="Record human administrative intake review")
    r.add_argument("id")
    r.add_argument("--reviewer", required=True)
    r.add_argument("--note", required=True)
    args = parser.parse_args()
    if args.command == "import": import_data(args.ai)
    elif args.command == "list": list_records()
    elif args.command == "show": show(args.id)
    elif args.command == "review": review(args.id, args.reviewer, args.note)


if __name__ == "__main__":
    main()
