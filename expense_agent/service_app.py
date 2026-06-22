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
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.workflow.utils._workflow_hitl_utils import REQUEST_INPUT_FUNCTION_CALL_NAME
from google.genai import types
from google.adk.cli.fast_api import get_fast_api_app

from expense_agent.agent import root_agent

# Use standard Python logging for console logs (no Google Cloud Logging used here)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ambient_expense_agent")

# Initialize the FastAPI App using ADK's built-in get_fast_api_app with web=True.
# This serves the ADK Playground Dev UI and builder endpoints on the same port!
app = get_fast_api_app(
    agents_dir="expense_agent",
    web=True,
    otel_to_cloud=False,
)

# Setup session service and runner using local Sqlite database
os.makedirs("expense_agent/.adk", exist_ok=True)
db_path = "expense_agent/.adk/session.db"
session_service = SqliteSessionService(db_path=db_path)

# Runner initialization referencing the main workflow
# App name matches the folder "expense_agent" to align with ADK session lookup
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    app_name="expense_agent",
)

# Explicitly ensure that OpenTelemetry exports to Cloud are disabled.
# This aligns with the developer checklist requirement: otel_to_cloud=False.
os.environ["OTEL_TO_CLOUD"] = "False"


def normalize_subscription(subscription_path: str | None) -> str:
    """
    Gotcha: Pub/Sub sends a fully-qualified subscription path,
    e.g., 'projects/my-project/subscriptions/my-subscription'.
    We normalize it down to the short name 'my-subscription' to
    keep session records and database entries readable.
    """
    if not subscription_path:
        return "default-subscription"
    return subscription_path.split("/")[-1]


@app.post("/pubsub")
@app.post("/")
async def handle_pubsub(request: Request):
    """
    Primary endpoint that accepts Pub/Sub trigger messages or raw expense payloads.
    Feeds each message into the workflow, supporting both initial execution and HITL resumption.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse request body as JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info(f"Received request body: {body}")

    # Determine if this is wrapped in a Pub/Sub message structure
    is_pubsub = isinstance(body, dict) and "message" in body
    
    # Extract subscription path and normalize it
    subscription_path = None
    if is_pubsub:
        subscription_path = body.get("subscription")
    
    session_id = normalize_subscription(subscription_path)
    user_id = session_id
    logger.info(f"Normalized subscription path to session_id: {session_id}")

    # Detect if this is a human decision response
    is_decision = False
    decision_data = None

    if is_pubsub:
        msg_wrapper = body["message"]
        raw_data = msg_wrapper.get("data")
        if raw_data:
            parsed_data = None
            try:
                # Decoded data might be base64-encoded in real Pub/Sub
                decoded = base64.b64decode(raw_data).decode("utf-8")
                parsed_data = json.loads(decoded)
            except Exception:
                # Fall back to plain JSON parsing
                try:
                    parsed_data = json.loads(raw_data)
                except Exception:
                    pass
            if isinstance(parsed_data, dict) and "approved" in parsed_data:
                is_decision = True
                decision_data = parsed_data
    else:
        # Check direct payload
        if isinstance(body, dict) and "approved" in body:
            is_decision = True
            decision_data = body

    if is_decision:
        approved = decision_data.get("approved", False)
        reason = decision_data.get("reason", "No reason provided")
        logger.info(f"Processing human decision: approved={approved}, reason={reason}")

        # Ensure session exists to resume
        existing_session = await session_service.get_session(
            app_name="expense_agent", user_id=user_id, session_id=session_id
        )
        if not existing_session:
            logger.error(f"Active session '{session_id}' not found to resume.")
            raise HTTPException(
                status_code=404,
                detail=f"Active session '{session_id}' not found to resume."
            )

        # Construct the resume message response schema
        resume_message = types.Content(
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id="human_approval_interrupt",
                        name=REQUEST_INPUT_FUNCTION_CALL_NAME,
                        response={"approved": approved, "reason": reason},
                    )
                )
            ]
        )

        logger.info(f"Resuming session '{session_id}'...")
        events = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=resume_message,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            events.append(event)
            logger.info(f"Resumed Event: {event.node_name} | {type(event).__name__}")

        final_event = events[-1] if events else None
        output = final_event.output if final_event else None
        logger.info(f"Session '{session_id}' resumed. Output: {output}")
        return {
            "status": "RESUMED",
            "session_id": session_id,
            "events_emitted": [e.node_name for e in events],
            "output": output,
        }

    else:
        # This is a new expense trigger
        logger.info(f"Processing new expense trigger")
        
        # Reset/delete the old session of the same name to start clean
        await session_service.delete_session(
            app_name="expense_agent", user_id=user_id, session_id=session_id
        )
        
        # Initialize a new session
        session = await session_service.create_session(
            app_name="expense_agent", user_id=user_id, session_id=session_id
        )

        # Set up content format
        if is_pubsub:
            msg_wrapper = body["message"]
            message_content = json.dumps(msg_wrapper)
        else:
            message_content = json.dumps({"data": body})

        new_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message_content)]
        )

        logger.info(f"Starting workflow for session '{session_id}'...")
        events = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            events.append(event)
            logger.info(f"Event: {event.node_name} | {type(event).__name__}")

        final_event = events[-1] if events else None
        output = final_event.output if final_event else None
        
        # Check if paused at the human input node
        is_paused = False
        pause_message = None
        if final_event and final_event.long_running_tool_ids and "human_approval_interrupt" in final_event.long_running_tool_ids:
            is_paused = True
            if final_event.content and final_event.content.parts:
                for part in final_event.content.parts:
                    if part.function_call and part.function_call.name == REQUEST_INPUT_FUNCTION_CALL_NAME:
                        pause_message = part.function_call.args.get("message")

        if is_paused:
            logger.info(f"Session '{session_id}' paused waiting for human decision")
            return {
                "status": "PAUSED",
                "session_id": session_id,
                "message": pause_message or "Awaiting human approval decision",
                "events_emitted": [e.node_name for e in events],
            }
        else:
            logger.info(f"Session '{session_id}' completed. Output: {output}")
            return {
                "status": "COMPLETED",
                "session_id": session_id,
                "events_emitted": [e.node_name for e in events],
                "output": output,
            }
