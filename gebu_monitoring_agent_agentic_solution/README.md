# GEBU Monitoring Agent

`gebu_monitoring_agent` is a sophisticated multi-agent system built with the Google Agent Development Kit (ADK). It is designed to autonomously detect, analyze, and report CPU drift in Google Kubernetes Engine (GKE) clusters.

The agent automates a three-stage pipeline: **Validation**, **Enrichment**, and **Notification**, ensuring that infrastructure alerts are accurately verified and that SRE teams receive high-quality, actionable reports.

## 🚀 Key Features

- **Multi-Agent Orchestration:** Uses a deterministic `SequentialAgent` workflow to coordinate specialized agents.
- **Shared Session Context:** Seamless data sharing between agents using ADK session state.
- **Intelligent Log Analysis:** Automatically parses GKE logs for CPU drift signals (e.g., `FailedScheduling`, `OOMKilled`, `CPUThrottlingHigh`).
- **Firestore Integration:** Comprehensive persistence for work items, incident enrichments, action transitions, and notification logs.
- **Cloud Storage Mapping:** Dynamically resolves cluster ownership from centralized mapping files in GCS.
- **Automated SRE Reporting:** Generates detailed Markdown-based SRE summaries and delivers them via SMTP.

## 🏗️ Architecture

The system consists of a **Root Agent** orchestrating three specialized sub-agents:

1.  **Validation Agent (`validation-agent`):** Gatekeeper that verifies the existence of work items and linked incidents in Firestore.
2.  **Enrichment Agent (`enrichment-agent`):** Interrogates Cloud Logging, aggregates telemetry, and compiles a detailed SRE executive summary.
3.  **Notification Agent (`notification-agent`):** Resolves the cluster owner's email and dispatches the SRE report via SMTP.

### Project Structure

```
gebu_monitoring_agent/
├── gebu_monitoring_agent/      # Core agent application
│   ├── agent.py                # Main agent logic and pipeline definition
│   ├── cloud_event_handler.py  # Handler for incoming Cloud Events
│   ├── fast_api_app.py         # FastAPI server for agent deployment
│   ├── app_utils/              # Shared utilities and types
│   └── sub_agents/             # Sub-agent implementations
│       ├── enrichment_agent/   # Enrichment agent logic
│       ├── notification_agent/ # Notification agent logic
│       └── validation_agent/   # Validation agent logic
├── skills/                     # Specialized agent skill definitions
│   ├── enrichment-agent/       # Enrichment agent skill
│   ├── notification-agent/     # Notification agent skill
│   ├── root-agent/             # Root agent skill
│   └── validation-agent/       # Validation agent skill
├── tests/                      # Unit and integration tests
├── GEMINI.md                   # Development and Evaluation guide
├── agents-cli-manifest.yaml    # Project metadata and configuration
└── pyproject.toml              # Dependencies and project settings
```

## 🛠️ Getting Started

### Prerequisites

- **uv**: Python package manager - [Install](https://docs.astral.sh/uv/getting-started/installation/)
- **agents-cli**: Google Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For authentication and GCP services - [Install](https://cloud.google.com/sdk/docs/install)

### Setup & Development

1.  **Install dependencies:**
    ```bash
    agents-cli install
    ```

2.  **Run the local playground:**
    Test your agent interactively in the web-based playground.
    ```bash
    agents-cli playground
    ```

3.  **Run evaluations:**
    Verify agent performance against your eval datasets.
    ```bash
    agents-cli eval generate
    agents-cli eval grade
    ```

## 🚀 Deployment

The project is configured for deployment to **Google Cloud Run**.

1.  **Configure your project:**
    ```bash
    gcloud config set project <YOUR_PROJECT_ID>
    ```

2.  **Deploy:**
    ```bash
    agents-cli deploy
    ```

## 📊 Observability & Persistence

- **Firestore:** Tracking in `work_items`, `actions`, `incident_enrichments`, `incident_summaries`, and `notifications`.
- **Cloud Logging:** Raw telemetry sourced from `k8s_cluster` and `k8s_node` resource types.
- **Cloud Trace:** Integrated ADK telemetry for pipeline execution tracing.

---
Built with the [Google Agent Development Kit (ADK)](https://github.com/google/ai-agent-sdk).
