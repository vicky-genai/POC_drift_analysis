---
name: notification-agent
description: Emails the compiled SRE summary report to the GKE cluster owner retrieved from GCS using custom SMTP, and logs results in Firestore.
---
# Notification Agent Skill

## Purpose
This skill defines the behavior of the `notification_agent`. You deliver the compiled SRE summary report to the verified owner of the GKE cluster.

## Instructions & Workflow
You MUST execute these exact steps in order:

1. **Extract Parameters**:
   - Retrieve the target `work_item_id` and `cluster_name` from `{validation_data}`.
   - Retrieve the full SRE summary report content from `{enrichment_summary}`.

2. **Dispatch Notification**:
   - Call the `send_incident_email_notification` tool. Pass:
     - `work_item_id` (from `{validation_data[work_item_id]}`)
     - `cluster_name` (from `{validation_data[cluster_name]}`)
     - `summary_content` (the full text of `{enrichment_summary}`)

3. **Handle Response**:
   - Confirm to the execution log whether the SRE report was successfully sent or if any delivery failures occurred.

## Tools
- `send_incident_email_notification`: Resolves the cluster owner's email address from GCS mapping, delivers the email via custom SMTP, and writes tracking telemetry directly to the Firestore `notifications` collection.