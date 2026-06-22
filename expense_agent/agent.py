# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import re
from typing import Any
from dotenv import load_dotenv

from pydantic import BaseModel, Field

from google.adk.agents import Context
from google.adk.workflow import Workflow, node
from google.adk.apps import App
from google.adk.events import Event, RequestInput
from google.genai import Client
from google.genai import types

from expense_agent.config import THRESHOLD, MODEL_NAME

# Load environment variables
load_dotenv()


# Pydantic Schemas
class RiskReview(BaseModel):
    risk_factors: list[str] = Field(
        description="List of risk factors or policy violations identified."
    )
    has_risk: bool = Field(
        description="True if there is elevated risk, False otherwise."
    )
    risk_summary: str = Field(
        description="A short explanation of the risk assessment."
    )


class HumanDecision(BaseModel):
    approved: bool = Field(description="True if approved, False if rejected.")
    reason: str | None = Field(
        default="No reason provided",
        description="Reason for approval or rejection."
    )


# Security Helpers
def detect_prompt_injection(text: str) -> bool:
    """Detects possible prompt injection patterns in the description."""
    text_lower = text.lower()
    injection_keywords = [
        "ignore prior", "ignore previous", "ignore all",
        "system prompt", "system instruction", "override",
        "auto-approve", "auto approve", "bypass", "ignore rules",
        "set status", "approved", "rejected", "you are now",
        "do not review", "force approval"
    ]
    return any(kw in text_lower for kw in injection_keywords)


# Workflow Nodes
def parse_expense(node_input: Any) -> Event:
    """Parses incoming JSON or base64-encoded Pub/Sub data to extract expense info."""
    if isinstance(node_input, types.Content):
        texts = []
        for part in node_input.parts or []:
            if part.text is not None:
                texts.append(part.text)
        node_input = "".join(texts)

    data_payload = None
    if isinstance(node_input, dict):
        if "data" in node_input:
            data_payload = node_input["data"]
        else:
            data_payload = node_input
    elif isinstance(node_input, str):
        try:
            parsed = json.loads(node_input)
            if isinstance(parsed, dict) and "data" in parsed:
                data_payload = parsed["data"]
            else:
                data_payload = parsed
        except json.JSONDecodeError:
            data_payload = node_input

    # Parse data_payload if base64-encoded or a JSON string
    parsed_data = None
    if isinstance(data_payload, str):
        # Try base64 decoding first
        try:
            decoded = base64.b64decode(data_payload).decode("utf-8")
            parsed_data = json.loads(decoded)
        except Exception:
            # Fall back to parsing as plain JSON
            try:
                parsed_data = json.loads(data_payload)
            except json.JSONDecodeError:
                pass
    elif isinstance(data_payload, dict):
        parsed_data = data_payload

    if not isinstance(parsed_data, dict):
        raise ValueError(f"Could not parse expense report from input: {node_input}")

    expense = {
        "amount": float(parsed_data.get("amount", 0.0)),
        "submitter": str(parsed_data.get("submitter", "Unknown")),
        "category": str(parsed_data.get("category", "Uncategorized")),
        "description": str(parsed_data.get("description", "")),
        "date": str(parsed_data.get("date", "")),
    }

    # Route conditionally based on amount
    if expense["amount"] < THRESHOLD:
        return Event(output=expense, route="auto_approve")
    else:
        return Event(output=expense, route="review")


def auto_approve(node_input: dict) -> dict:
    """Directly auto-approves expenses under the threshold."""
    return {
        "status": "APPROVED",
        "expense": node_input,
        "review": {
            "risk_factors": [],
            "has_risk": False,
            "risk_summary": "Auto-approved: amount is under the $100 threshold.",
        },
        "decision": {
            "approved": True,
            "reason": "System auto-approved (under threshold).",
        },
    }


def security_checkpoint(ctx: Context, node_input: dict) -> Event:
    """Scrubs PII (SSN & Credit Cards) and defends against prompt injections."""
    expense = dict(node_input)
    description = expense.get("description", "")
    redacted_categories = []

    # 1. Scrub SSNs: XXX-XX-XXXX
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    if re.search(ssn_pattern, description):
        description = re.sub(ssn_pattern, "[REDACTED_SSN]", description)
        redacted_categories.append("SSN")

    # 2. Scrub Credit Cards: 13-16 digits, optional spaces/dashes
    cc_pattern = r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b'
    if re.search(cc_pattern, description):
        description = re.sub(cc_pattern, "[REDACTED_CC]", description)
        redacted_categories.append("Credit Card")

    # Save cleaned description back to the expense dictionary
    expense["description"] = description

    # Save state variables for human/downstream nodes
    ctx.state["redacted_categories"] = redacted_categories
    ctx.state["expense"] = expense

    # 3. Defend against Prompt Injection
    if detect_prompt_injection(description):
        ctx.state["security_alert"] = True
        return Event(output=expense, route="bypass_to_human")

    ctx.state["security_alert"] = False
    return Event(output=expense, route="proceed_to_llm")


def review_expense(ctx: Context, node_input: dict) -> dict:
    """Uses LLM to evaluate the expense details for risk factors."""
    # Store expense details in state for the HITL step to access on resume
    ctx.state["expense"] = node_input

    client = Client()
    prompt = f"""
    You are an automated risk assessment assistant for expense approvals.
    Review the following expense report details for any anomalies, policy violations, or risk factors:
    {json.dumps(node_input, indent=2)}
    
    Identify risk factors and determine if there is an elevated risk (e.g. unusually high amounts for the category, vague descriptions, inappropriate categorization).
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RiskReview,
        ),
    )

    try:
        review_data = json.loads(response.text)
    except Exception:
        review_data = {
            "risk_factors": ["Failed to parse model response"],
            "has_risk": True,
            "risk_summary": response.text or "Error parsing review output",
        }

    # Store review in state
    ctx.state["review"] = review_data

    return {
        "expense": node_input,
        "review": review_data,
    }


@node(rerun_on_resume=True)
def human_approval(ctx: Context, node_input: dict) -> Any:
    """Requests human approval and resumes to process the decision."""
    interrupt_id = "human_approval_interrupt"

    if interrupt_id in ctx.resume_inputs:
        # Resuming from human response
        decision = ctx.resume_inputs[interrupt_id]
        expense = ctx.state.get("expense")
        review = ctx.state.get("review")
        security_alert = ctx.state.get("security_alert", False)
        redacted_categories = ctx.state.get("redacted_categories", [])

        approved = decision.get("approved", False)
        return {
            "status": "APPROVED" if approved else "REJECTED",
            "expense": expense,
            "review": review,
            "decision": decision,
            "security_alert": security_alert,
            "redacted_categories": redacted_categories,
        }

    # First run: pause and yield RequestInput
    expense = ctx.state.get("expense") or node_input.get("expense")
    review = ctx.state.get("review") or node_input.get("review")
    security_alert = ctx.state.get("security_alert", False)
    redacted_categories = ctx.state.get("redacted_categories", [])

    msg_lines = []
    if security_alert:
        msg_lines.append(
            "⚠️ SECURITY WARNING: Possible prompt injection attempt detected in the description. The LLM review was bypassed."
        )
    if redacted_categories:
        msg_lines.append(
            f"🔒 PII REDACTED: Personal data was scrubbed ({', '.join(redacted_categories)})."
        )

    msg_lines.append(
        f"Expense review request: Submitter {expense.get('submitter')} submitted "
        f"${expense.get('amount')} for {expense.get('category')}."
    )
    msg_lines.append(f"Description: {expense.get('description')}")

    if review:
        review_summary = review.get("risk_summary", "No summary provided")
        risk_factors = review.get("risk_factors", [])
        msg_lines.append(f"Risk Summary: {review_summary}")
        msg_lines.append(
            f"Risk Factors: {', '.join(risk_factors) if risk_factors else 'None'}"
        )
    else:
        msg_lines.append("Risk Assessment: Bypassed due to security checkpoint.")

    msg_lines.append("Please approve or reject this expense.")
    message = "\n".join(msg_lines)

    return RequestInput(
        interrupt_id=interrupt_id,
        message=message,
        response_schema=HumanDecision,
    )


def record_outcome(node_input: dict) -> dict:
    """Logs the final approval/rejection outcome and outputs it."""
    status = node_input.get("status")
    expense = node_input.get("expense")
    return {
        "status": status,
        "expense": expense,
        "review": node_input.get("review"),
        "decision": node_input.get("decision"),
        "security_alert": node_input.get("security_alert", False),
        "redacted_categories": node_input.get("redacted_categories", []),
    }


# Workflow Graph Definition
root_agent = Workflow(
    name="root_agent",
    edges=[
        ("START", parse_expense),
        (
            parse_expense,
            {"auto_approve": auto_approve, "review": security_checkpoint},
        ),
        (
            security_checkpoint,
            {
                "proceed_to_llm": review_expense,
                "bypass_to_human": human_approval,
            },
        ),
        (review_expense, human_approval),
        (human_approval, record_outcome),
        (auto_approve, record_outcome),
    ],
)

app = App(
    root_agent=root_agent,
    name="expense_agent",
)
