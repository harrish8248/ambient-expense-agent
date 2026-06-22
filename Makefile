# Makefile for ambient-expense-agent

.PHONY: install playground serve generate-traces grade

install:
	agents-cli install

playground:
	uv run uvicorn expense_agent.service_app:app --host 127.0.0.1 --port 8080

serve:
	uv run uvicorn expense_agent.service_app:app --host 127.0.0.1 --port 8080

generate-traces:
	uv run python tests/eval/generate_traces.py

grade:
	C:\Users\harri\AppData\Local\Programs\Python\Python313\python.exe tests/eval/run_grade.py eval grade --config tests/eval/eval_config.yaml --traces artifacts/traces/generated_traces.json --output artifacts/grade_results/ --project dummy-project

