# Project Setup and Execution Plan

This document outlines the steps to set up, run, and deploy the `gebu_monitoring_agent` project.

## 1. Clone the Project
Clone the repository from Git to your local machine:
```bash
git clone <REPOSITORY_URL>
cd gebu_monitoring_agent
```

## 2. Install Dependencies
Use `uv` (recommended) or `pip` to install the required libraries:

**Using agents-cli (recommended):**
```bash
uv tool install google-agents-cli
agents-cli install
```

**Using pip:**
```bash
pip install -r requirements.txt
```

## 3. Local Testing Workflow

There are two primary ways to test the agent and its workflow locally:

### Option A: Interactive Testing with ADK Web Interface

This method allows you to interact directly with the agent through a web UI, ideal for testing individual agent logic and immediate feedback.

1.  **Run the ADK Web Interface:**
    ```bash
    agents-cli web
    ```
    This command will launch the ADK web interface, where your agents will be running locally, and you can interact with them directly.

2.  **Interact with the Agent:**
    After starting the web interface, you can provide input to the agent, simulating triggers or user queries to observe its processing logic.

### Option B: End-to-End Workflow Testing with FastAPI and Mock CloudEvents

This method simulates the entire deployment environment locally, including the FastAPI application handling CloudEvents, allowing you to verify the complete workflow, including Eventarc JSON/Protobuf schema parsing and session coordination.

1.  **Start the FastAPI Application:**
    In a dedicated terminal, run the FastAPI application:
    ```bash
    uvicorn gebu_monitoring_agent.fast_api_app:app --reload
    ```
    This will start the application, which includes the endpoint for receiving CloudEvents.

2.  **Create Work Item in Firestore (Optional, for full context):**
    For a complete end-to-end simulation where the agent needs to fetch work item details, ensure a work item exists in your Firestore. You would typically do this through your application's UI or a direct Firestore write. For local testing, you might manually add a document or use a Firestore client library.

3.  **Mock CloudEvent using `send_cloudevent.py`:**
    In another terminal, use the `send_cloudevent.py` script to send a mock CloudEvent to your locally running FastAPI application. This script is configured to send a Firestore document creation event.

    ```bash
    python send_cloudevent.py
    ```
    Ensure that `GCP_PROJECT_ID` and `FIRESTORE_DATABASE_NAME_IN_EVENT` are correctly configured in `send_cloudevent.py` to match your testing environment.

    This script will send a POST request to `http://localhost:8000/cloudevent`, mimicking an Eventarc trigger. Your FastAPI application's `cloud_event_handler` will then process this event, allowing you to verify how it parses Eventarc JSON/Protobuf schemas and coordinates sessions.

## 4. Deploy to Google Cloud Run
Deploy the agent as a serverless service:

1. **Configure Project:**
   ```bash
   gcloud config set project <YOUR_PROJECT_ID>
   ```

2. **Deploy via agents-cli:**
   ```bash
   agents-cli deploy
   ```
   *Follow the prompts to select the region (default: us-central1).*

## 7. Configure Firestore & Eventarc Trigger

### Step 1: Create the Firestore Database
Ensure you have a Firestore database (referenced in `gebu_monitoring_agent/agent.py`).
1. Go to **Firestore** in the GCP Console.
2. Click **Create Database**.
3. Select **Native Mode**.
4. Set Database ID as needed.

### Step 2: Create Eventarc Trigger
Configure Eventarc to listen for document creation in Firestore and trigger the Cloud Run service.()

1. Go to **Eventarc** > **Triggers**.
2. Click **Create Trigger**.
3. **Trigger Name:** `trigger-name`.
4. **Trigger Type:** `Google sources` > `Cloud Firestore`.
5. **Event Type:** `google.cloud.firestore.document.v1.created`.
6. **Database:** `database-name`.
7. **Document Path:** `work_items/{work_item_id}` (matches the handler logic).
8. **Destination:** `Cloud Run service`.
9. **Service Name:** `deployed-service-name` (or your deployed service name).
10. **URL Path:** `/cloudevent`.
11. **Service Account:** Ensure the service account has `roles/eventarc.eventReceiver` and `roles/run.invoker` permissions.

Click **Create**. Now, whenever a new document is added to the `work_items` collection in the `database-name` database, the agent will automatically trigger the analysis pipeline.
