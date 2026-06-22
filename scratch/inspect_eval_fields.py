from vertexai._genai.types.common import EvaluationDataset, EvalCase

print("EvaluationDataset fields:")
for k, v in EvaluationDataset.model_fields.items():
    print(f"  {k}: {v.annotation}")

print("\nEvalCase fields:")
for k, v in EvalCase.model_fields.items():
    print(f"  {k}: {v.annotation}")
