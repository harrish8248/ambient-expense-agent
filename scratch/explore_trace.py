import json
import os
from dotenv import load_dotenv

# Set dummy project to satisfy vertexai/adk initialization
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "dummy-project")
load_dotenv()

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from expense_agent.agent import root_agent

def main():
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    payload = {
        "data": {
            "amount": 45.0,
            "submitter": "Alice",
            "category": "Meals",
            "description": "Lunch with client",
            "date": "2026-06-18",
        }
    }
    message = types.Content(
        role="user", parts=[types.Part.from_text(text=json.dumps(payload))]
    )

    list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )

    print(f"Number of events in session: {len(session.events)}")
    for i, event in enumerate(session.events):
        print(f"Event {i}: {type(event)}, author={event.author}, output={event.output}")

if __name__ == "__main__":
    main()
