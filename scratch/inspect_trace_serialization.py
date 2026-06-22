import json
import asyncio
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from expense_agent.agent import root_agent

async def test_trace():
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name="expense_agent", user_id="user", session_id="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="expense_agent")
    
    # Just run a simple $50 auto-approval case
    payload = {"data": {"amount": 50.0, "submitter": "alice@company.com", "category": "software", "description": "IDE License", "date": "2026-06-06"}}
    msg = types.Content(role="user", parts=[types.Part.from_text(text=json.dumps(payload))])
    
    events = []
    async for e in runner.run_async(user_id="user", session_id=session.id, new_message=msg):
        events.append(e)
    
    # Fetch session to see trace serialization
    session = await session_service.get_session(app_name="expense_agent", user_id="user", session_id="test")
    
    # Dump session details
    print("Session fields:")
    for k, v in session.__dict__.items():
        if k != "events":
            print(f"  {k}: {type(v)}")
        else:
            print(f"  events count: {len(v)}")
            if len(v) > 0:
                print("  first event type:", type(v[0]))
                print("  first event schema:", v[0].model_dump())

if __name__ == "__main__":
    asyncio.run(test_trace())
