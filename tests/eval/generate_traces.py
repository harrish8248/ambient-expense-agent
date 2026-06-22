import json
import os
from dotenv import load_dotenv

# Set dummy project to satisfy vertexai/adk initialization
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "dummy-project")
load_dotenv()

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow.utils._workflow_hitl_utils import REQUEST_INPUT_FUNCTION_CALL_NAME
from google.genai import types

# Import Pydantic models for evaluation traces
from vertexai._genai.types.common import EvaluationDataset, EvalCase, ResponseCandidate
from vertexai._genai.types.evals import AgentData, ConversationTurn, AgentEvent

from expense_agent.agent import root_agent, detect_prompt_injection

def main():
    # Path to dataset and output
    dataset_path = "tests/eval/datasets/basic-dataset.json"
    output_path = "artifacts/traces/generated_traces.json"
    
    # Load dataset
    print(f"Loading dataset from {dataset_path}...")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset_data = json.load(f)
    
    eval_cases_input = dataset_data.get("eval_cases", [])
    eval_cases_output = []
    
    # Setup runner
    session_service = InMemorySessionService()
    
    for i, case_data in enumerate(eval_cases_input):
        case_id = case_data.get("eval_case_id", f"case_{i}")
        prompt_parts = case_data.get("prompt", {}).get("parts", [])
        prompt_text = prompt_parts[0].get("text", "") if prompt_parts else ""
        
        print(f"\nProcessing case: {case_id}")
        print(f"Prompt: {prompt_text}")
        
        # Create new session for this case
        session = session_service.create_session_sync(user_id=f"user_{case_id}", app_name="expense-eval")
        runner = Runner(agent=root_agent, session_service=session_service, app_name="expense-eval")
        
        prompt_content = types.Content(
            role="user", parts=[types.Part.from_text(text=prompt_text)]
        )
        
        # Run step 1
        print("  Running workflow step 1...")
        events_run1 = list(
            runner.run(
                new_message=prompt_content,
                user_id=f"user_{case_id}",
                session_id=session.id,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            )
        )
        
        # Check for HITL
        last_event = events_run1[-1]
        is_hitl = False
        if last_event.long_running_tool_ids and "human_approval_interrupt" in last_event.long_running_tool_ids:
            is_hitl = True
            
        if is_hitl:
            print("  Human Approval required. Intercepting...")
            # Extract description to decide approved/rejected
            try:
                payload = json.loads(prompt_text)
                if "data" in payload:
                    expense_data = payload["data"]
                else:
                    expense_data = payload
            except Exception:
                expense_data = {"description": prompt_text}
                
            description = expense_data.get("description", "")
            
            # Automated decision logic: approves clean requests, rejects prompt injections
            if detect_prompt_injection(description):
                approved = False
                reason = "Rejected automated decision: security checkpoint detected prompt injection attempt."
                print("    Decision: REJECTED (Prompt Injection)")
            else:
                approved = True
                reason = "Approved automated decision: expense request is clean."
                print("    Decision: APPROVED (Clean Request)")
                
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
            
            print("  Resuming workflow step 2...")
            events_run2 = list(
                runner.run(
                    new_message=resume_message,
                    user_id=f"user_{case_id}",
                    session_id=session.id,
                    run_config=RunConfig(streaming_mode=StreamingMode.SSE),
                )
            )
            
            final_event = events_run2[-1]
            
            # Construct turns
            turn0 = ConversationTurn(
                turn_index=0,
                events=[
                    AgentEvent(author="user", content=prompt_content),
                    AgentEvent(author="agent", content=last_event.content)
                ]
            )
            turn1 = ConversationTurn(
                turn_index=1,
                events=[
                    AgentEvent(author="user", content=resume_message),
                    AgentEvent(
                        author="agent",
                        content=types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=json.dumps(final_event.output))]
                        )
                    )
                ]
            )
            turns = [turn0, turn1]
        else:
            print("  Workflow completed without human intervention (Auto-approved).")
            final_event = last_event
            turn0 = ConversationTurn(
                turn_index=0,
                events=[
                    AgentEvent(author="user", content=prompt_content),
                    AgentEvent(
                        author="agent",
                        content=types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=json.dumps(final_event.output))]
                        )
                    )
                ]
            )
            turns = [turn0]
            
        # Create responses candidate
        responses = [
            ResponseCandidate(
                response=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=json.dumps(final_event.output))]
                )
            )
        ]
        
        agent_data = AgentData(turns=turns)
        
        eval_case = EvalCase(
            eval_case_id=case_id,
            prompt=prompt_content,
            responses=responses,
            agent_data=agent_data
        )
        
        eval_cases_output.append(eval_case)
        print(f"  Final status: {final_event.output.get('status')}")
        
    # Construct EvaluationDataset
    dataset_output = EvaluationDataset(eval_cases=eval_cases_output)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to file using Pydantic's serialization
    print(f"\nSaving generated traces to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(dataset_output.model_dump_json(by_alias=True, indent=2))
        
    print("Done!")

if __name__ == "__main__":
    main()
