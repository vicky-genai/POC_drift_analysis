"""
This script is used to test the entire workflow locally, verifying how it parses Eventarc JSON/Protobuf schemas, coordinates sessions, and mocks the FastAPI HTTP endpoint.
"""

import datetime
import json
import os
import uuid

import requests


def generate_firestore_cloudevent_payload(
    project_id: str,
    work_item_id: str,
    collection_name: str = "work_items",
    database_name: str = "(default)",
) -> dict:
    """Generates a dictionary payload for a Firestore document creation CloudEvent.

    Args:
        project_id: Your Google Cloud Project ID.
        work_item_id: The ID of the work item document that was created.
        collection_name: The Firestore collection name (default: "work_items").
        database_name: The Firestore database name (e.g., "(default)" or a named database).

    Returns:
        A dictionary representing the CloudEvent payload.
    """
    event_id = str(uuid.uuid4())
    timestamp = (
        datetime.datetime.now(datetime.UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    document_path = (
        f"projects/{project_id}/databases/{database_name}/documents/"
        f"{collection_name}/{work_item_id}"
    )

    payload = {
        "specversion": "1.0",
        "type": "google.cloud.firestore.document.v1.created",
        "source": f"//firestore.googleapis.com/projects/{project_id}/databases/{database_name}",
        "id": event_id,
        "time": timestamp,
        "datacontenttype": "application/json",
        "data": {
            "oldValue": {},
            "updateMask": {},
            "value": {
                "name": document_path,
                "fields": {
                    "title": {"stringValue": f"Work Item: {work_item_id}"},
                    "description": {
                        "stringValue": (
                            f"This is a test work item for {work_item_id} created at {timestamp}."
                        )
                    },
                },
                "createTime": timestamp,
                "updateTime": timestamp,
            },
        },
    }
    return payload


if __name__ == "__main__":
    # --- IMPORTANT: Configure these values ---
    # Replace with your actual GCP project ID. You can set it as an environment variable
    # or directly here. Example: export GCP_PROJECT_ID="your-project-id-123"
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")

    # Change this ID for different tests to simulate new work items
    TEST_WORK_ITEM_ID = f"test-work-item-{uuid.uuid4().hex[:8]}"

    # This refers to the database name as it appears in the CloudEvent payload.
    # Typically, for the primary Firestore database, this is "(default)".
    # If Eventarc is configured to target a named database (e.g., "drift-monitor")
    # and the event payload's 'source' and 'name' fields reflect that, adjust here.
    FIRESTORE_DATABASE_NAME_IN_EVENT = "drift-monitor"

    TARGET_URL = "http://localhost:8000/cloudevent"

    if GCP_PROJECT_ID == "your-gcp-project-id":
        print(
            "ERROR: GCP_PROJECT_ID is not set. Please set it as an environment variable "
            '(e.g., export GCP_PROJECT_ID="your-actual-project-id") or modify the script directly.'
        )
        exit(1)

    print(f"Generating CloudEvent for work_item_id: {TEST_WORK_ITEM_ID}")

    cloudevent_payload = generate_firestore_cloudevent_payload(
        project_id=GCP_PROJECT_ID,
        work_item_id=TEST_WORK_ITEM_ID,
        database_name=FIRESTORE_DATABASE_NAME_IN_EVENT,
    )

    headers = {
        "Content-Type": "application/json",
        # CloudEvent HTTP headers (optional, but good practice to include for clarity)
        "ce-id": cloudevent_payload["id"],
        "ce-source": cloudevent_payload["source"],
        "ce-type": cloudevent_payload["type"],
        "ce-specversion": cloudevent_payload["specversion"],
    }

    try:
        print(f"Sending CloudEvent to {TARGET_URL}...")
        response = requests.post(TARGET_URL, json=cloudevent_payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        print("\n--- Response from local server ---")
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))

    except requests.exceptions.ConnectionError:
        print(f"\nERROR: Could not connect to {TARGET_URL}.")
        print(
            "Please ensure your FastAPI application is running locally (from the other terminal window)."
        )
        print(
            "You can start it with: `uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000`"
        )
    except requests.exceptions.RequestException as e:
        print(f"\nERROR: An HTTP request error occurred: {e}")
        if "response" in locals() and response is not None:
            print(f"Response content: {response.text}")

    print(
        "\n--- To send this payload using curl (after starting your local server) ---"
    )
    # Generate a single-line JSON string for curl -d argument
    cloudevent_json_single_line = json.dumps(cloudevent_payload, separators=(",", ":"))

    print("curl -X POST \\")
    print("  -H 'Content-Type: application/json' \\")
    for header_name, header_value in headers.items():
        if header_name != "Content-Type":
            print(f"  -H '{header_name}: {header_value}' \\")
    print(f"  -d '{cloudevent_json_single_line}' \\")
    print(f"  {TARGET_URL}\n")

    print("--- Important reminders ---")
    print(
        f"- Ensure a document with ID '{TEST_WORK_ITEM_ID}' (or one accessible via your project ID) "
        "exists in the 'work_items' collection of your 'drift-monitor' Firestore database for the agent's validation tool to succeed."
    )
    print("- Check the terminal running your FastAPI application for detailed logs.")
