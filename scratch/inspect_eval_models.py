from vertexai._genai.types.common import EvaluationDataset, EvalCase
import json

print("EvaluationDataset schema:")
print(json.dumps(EvaluationDataset.model_json_schema(), indent=2))

print("\nEvalCase schema:")
print(json.dumps(EvalCase.model_json_schema(), indent=2))
