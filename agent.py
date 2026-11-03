"""Read-only AI intake assistant using synthetic mortgage applications."""
import json
import os
import sqlite3
import sys

from openai import OpenAI
from app import DB


def get_application_status(application_id):
    """Retrieve only intake-checklist data, not financial information."""
    if not DB.exists():
        return {"error": "Database not found. Run python3 app.py import first."}
    with sqlite3.connect(DB) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT application_id, status, missing_documents,
                      missing_fields, reviewer
               FROM applications WHERE application_id = ?""",
            (application_id,),
        ).fetchone()
    if row is None:
        return {"error": "Application not found."}
    return {
        "application_id": row["application_id"],
        "status": row["status"],
        "missing_documents": json.loads(row["missing_documents"]),
        "missing_fields": json.loads(row["missing_fields"]),
        "human_review_recorded": row["reviewer"] is not None,
    }


TOOLS = [{
    "type": "function",
    "name": "get_application_status",
    "description": "Look up intake completeness for one synthetic application ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "application_id": {"type": "string", "description": "ID such as APP-1002"}
        },
        "required": ["application_id"],
        "additionalProperties": False,
    },
    "strict": True,
}]


def ask_agent(question):
    if not os.getenv("OPENAI_API_KEY"):
        print("No API key found in this terminal.")
        return
    client = OpenAI()
    try:
        first = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions=(
                "You are a read-only intake assistant for synthetic mortgage data. "
                "Use the lookup tool to answer the user's application question. "
                "Only report retrieved facts, do not guess, and never make "
                "mortgage approval, denial, or creditworthiness recommendations. "
                "Remind users that a human must verify the findings."
            ),
            input=question,
            tools=TOOLS,
            tool_choice="required",
            parallel_tool_calls=False,
        )
        calls = [item for item in first.output if item.type == "function_call"]
        if len(calls) != 1 or calls[0].name != "get_application_status":
            print("Unexpected tool request; no tool executed.")
            return
        call = calls[0]
        arguments = json.loads(call.arguments)
        application_id = arguments.get("application_id", "")
        if not isinstance(application_id, str) or len(application_id) > 40:
            print("Invalid application ID.")
            return
        result = get_application_status(application_id)
        print("Tool called: get_application_status", application_id)
        second = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            previous_response_id=first.id,
            instructions=(
                "Summarize the tool result accurately. No approval or denial "
                "recommendations. Mention human verification."
            ),
            input=[{
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(result),
            }],
        )
        print("\nAssistant:", second.output_text)
    except Exception as error:
        print(f"API request failed: {type(error).__name__}")
        print("Check your API billing/limits and key; the database is unchanged.")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What is missing from APP-1002?"
    ask_agent(question)
