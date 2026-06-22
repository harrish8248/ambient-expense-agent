from vertexai._genai.types.common import EvaluationResult
import inspect

print("EvaluationResult fields:")
for k, v in EvaluationResult.model_fields.items():
    print(f"  {k}: {v.annotation}")
