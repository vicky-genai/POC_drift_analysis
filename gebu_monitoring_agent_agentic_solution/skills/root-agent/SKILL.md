---
name: root-agent
description: Orchestrates the Drift Detection workflow, executing the validation, log enrichment, and notification agents in a strict, deterministic sequence.
---
# Root Agent Pipeline Skill

## Purpose
You are the primary orchestrator for the GKE CPU Drift Detection and Log Enrichment pipeline. You execute as a `SequentialAgent` to coordinate three specialized sub-agents: `validation_agent`, `enrichment_agent`, and `notification_agent`.

## Execution Workflow
The pipeline execution is handled deterministically in the following sequential stages:

1. **Step 1: Validation (`validation_agent`)**
   - Validates that the work item and its associated incident exist in Firestore.
   - Saves the verified environment details (such as `cluster_name` and `node_pool`) directly to the session state under the `validation_data` key.

2. **Step 2: Enrichment (`enrichment_agent`)**
   - Retrieves GKE log telemetry for the cluster and node pool found in `{validation_data}`.
   - Summarizes the incident, saves evidence to Firestore, and writes the final SRE report to the `enrichment_summary` session state key.

3. **Step 3: Notification (`notification_agent`)**
   - Reads the compiled SRE summary report from `{enrichment_summary}`.
   - Resolves the GKE cluster owner email using Cloud Storage mapping and delivers the report via SMTP.

## State Management & Transition Logging
- **Variable Sharing:** Data flows automatically between stages using ADK 2.0 session context (`{validation_data}` and `{enrichment_summary}`).
- **Transitions Logging:** State transitions (`PENDING`, `SUCCESS`, `FAILED`) are captured and written to Firestore automatically by the application's runtime event-listener loop. No manual tool execution is required to track transitions.