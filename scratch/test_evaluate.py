import os
from dotenv import load_dotenv
load_dotenv()

# Set dummy project to satisfy vertexai Client initialization if needed
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "dummy-project")

import vertexai
from vertexai._genai.types.common import EvaluationDataset, EvalCase
from google.genai import types

# Initialize client using GEMINI_API_KEY
client = vertexai.Client()
print("Client initialized successfully.")

# Create a simple dataset and custom LLM metric to evaluate
case = EvalCase(
    eval_case_id="case1",
    prompt=types.Content(role="user", parts=[types.Part.from_text(text="Test prompt")]),
    responses=[types.Content(role="model", parts=[types.Part.from_text(text="Test response")])],
)
dataset = EvaluationDataset(eval_cases=[case])

# Custom LLM Metric
from vertexai._genai import types as vertex_types
metric = vertex_types.LLMMetric(
    name="test_metric",
    prompt_template="Score this response 1-5: {response}"
)

print("Running evaluate...")
try:
    result = client.evals.evaluate(dataset=dataset, metrics=[metric])
    print("Evaluate ran successfully!")
    print("Summary:", result.summary_metrics)
except Exception as e:
    print("Evaluate failed:", type(e), e)
