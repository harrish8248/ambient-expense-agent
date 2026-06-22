# 💸 Ambient Expense Agent

An intelligent, production-ready AI agent workflow built with the Google **Agent Development Kit (ADK)**. This agent automates the ingestion, security screening, risk assessment, and approval process of corporate expense reports with built-in **Human-in-the-Loop (HITL)** support.

---

## 🌟 Key Features

*   🤖 **Dual Agent Architecture**: Includes both a simple boilerplate assistant and a fully featured automated expense auditor workflow.
*   🔒 **Automated Security Guardrails**: Scrubs personal identifiable information (PII) like SSNs and credit cards, and flags prompt injection attempts to protect core LLM prompt integrity.
*   🧠 **LLM-Based Risk Analysis**: Evaluates expense details for potential policy violations or anomalies using **Gemini**.
*   👥 **Human-in-the-Loop (HITL)**: Automatically pauses execution when an expense needs review and resumes processing seamlessly upon receiving approval input.
*   ⚡ **FastAPI Integration**: Serves the agent playground and handles Pub/Sub events or HTTP webhooks for event-driven orchestration.
*   📊 **Local State & Observability**: Manages session state via SQLite and is pre-wired for Google Cloud Operations Suite telemetry.

---

## 🗺️ Agent Workflow Architecture

The core expense auditing workflow follows a structured sequence of checks and gates:

```mermaid
graph TD
    START([START]) --> parse[1. Parse Expense]
    
    parse -->|Amount < $100| auto_approve[Auto Approve]
    parse -->|Amount >= $100| security_check[2. Security Checkpoint]
    
    security_check -->|Safe| review_expense[3. LLM Risk Assessment]
    security_check -->|Prompt Injection Detected| human_approval[4. Human Approval Node]
    
    review_expense --> human_approval
    
    human_approval -->|Yield Interrupt & Resume| record_outcome[5. Record Outcome]
    auto_approve --> record_outcome
    
    classDef startEnd fill:#1A73E8,stroke:#1A73E8,color:#fff,font-weight:bold;
    classDef nodeStyle fill:#F1F3F4,stroke:#dadce0,color:#202124;
    classDef warnStyle fill:#FCE8E6,stroke:#F28B82,color:#C5221F;
    classDef successStyle fill:#E6F4EA,stroke:#81C995,color:#137333;
    
    class START startEnd;
    class parse,security_check,review_expense nodeStyle;
    class human_approval warnStyle;
    class auto_approve,record_outcome successStyle;
```

---

## 📂 Project Structure

```
ambient-expense-agent/
├── expense_agent/         # Primary automated auditing workflow
│   ├── agent.py               # Workflow graph nodes, security schemas & graph
│   ├── service_app.py         # FastAPI backend, SQLite setup, Pub/Sub webhook
│   └── config.py              # Model names and validation thresholds
├── app/                   # Scaffolded basic playground assistant
│   └── agent.py               # Simple weather & time agent logic
├── tests/                 # Unit, integration, and load tests
├── deployment/            # Terraform configurations (Single-project Setup)
├── GEMINI.md              # AI-assisted development instructions
└── pyproject.toml         # Python workspace dependencies (uv)
```

---

## 🚀 Quick Start

### Prerequisites

Ensure you have the following installed on your system:
*   [**uv**](https://docs.astral.sh/uv/getting-started/installation/) — Fast Python package and project manager.
*   [**google-agents-cli**](https://github.com/google/agents-cli) — Command Line Tool for ADK development.
*   [**Google Cloud SDK**](https://cloud.google.com/sdk/docs/install) — For GCP authentication and services.

### Installation

1. Install the CLI and download necessary tools/skills:
    ```bash
    uvx google-agents-cli setup
    ```

2. Install python dependencies locally:
    ```bash
    agents-cli install
    ```

3. Launch the interactive local playground UI to test the agent:
    ```bash
    agents-cli playground
    ```

---

## 🛠️ CLI Reference

Here is a quick overview of useful developer commands:

| Command | Category | Description |
| :--- | :--- | :--- |
| `agents-cli playground` | Development | Start a local web app with the interactive UI |
| `agents-cli lint` | Quality | Lint the codebase for formatting and type issues |
| `uv run pytest tests/` | Testing | Run all unit and integration tests |
| `agents-cli eval generate` | Evaluation | Run agent on dataset and output evaluation traces |
| `agents-cli eval grade` | Evaluation | Run LLM-as-judge graders on the output traces |
| `agents-cli eval compare` | Evaluation | Diff current evaluation grades against a prior run |
| `agents-cli deploy` | Deployment | Deploy the agent app to Vertex AI Agent Runtime |

---

## 🔒 Security & Safety Controls

> [!IMPORTANT]
> The security checkpoint node (`security_checkpoint`) runs automatically before submitting details to the LLM to prevent data leaks and prompt manipulation.

*   **PII Scrubbing**: Automatically replaces SSNs with `[REDACTED_SSN]` and Credit Cards with `[REDACTED_CC]` in the description.
*   **Prompt Injection Detection**: Scans for override keywords (like *"ignore prior instructions"*, *"force approval"*, etc.). If detected, it bypasses the LLM analysis entirely and escalates directly to human review with a `⚠️ SECURITY WARNING`.
