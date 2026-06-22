import os
from unittest.mock import MagicMock
import google.auth

# Mock credentials with universe_domain
def mock_default(*args, **kwargs):
    mock_creds = MagicMock()
    mock_creds.universe_domain = "googleapis.com"
    return mock_creds, "dummy-project"

google.auth.default = mock_default

from dotenv import load_dotenv
load_dotenv()

os.environ["GOOGLE_CLOUD_PROJECT"] = "dummy-project"

import vertexai
from vertexai._genai.types.common import EvaluationDataset, EvalCase, ResponseCandidate
from google.genai import types

client = vertexai.Client(project=None, location=None)

case = EvalCase(
    eval_case_id="case1",
    prompt=types.Content(role="user", parts=[types.Part.from_text(text="Test prompt")]),
    responses=[ResponseCandidate(response=types.Content(role="model", parts=[types.Part.from_text(text="Test response")]))],
)
dataset = EvaluationDataset(eval_cases=[case])

# Local custom metric
from vertexai._genai import types as vertex_types
def evaluate_fn(instance):
    return {'score': 5, 'explanation': 'Trivial score'}

metric = vertex_types.Metric(
    name="test_local_metric",
    custom_function=evaluate_fn
)

try:
    result = client.evals.evaluate(dataset=dataset, metrics=[metric])
    print("Evaluate ran successfully!")
    print("Summary:", result.summary_metrics)
    print("Case Results:")
    for cr in result.eval_case_results:
        print(cr.model_dump())
except Exception as e:
    print("Evaluate failed:", type(e), e)
