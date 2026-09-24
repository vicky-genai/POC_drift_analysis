# import json
# from datetime import UTC, datetime

# import google.auth
# from fastapi import APIRouter, HTTPException, Request
# from google.adk.errors.already_exists_error import AlreadyExistsError
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService
# from google.cloud import firestore
# from google.cloud import logging as cloud_logging
# from google.genai import types

# from app.agent import root_agent
# from tools.tools import set_action_transitions

# router = APIRouter()

# # Clients & Initialization
# _, project_id = google.auth.default()
# db = firestore.Client(project=project_id, database="drift-monitor")
# logging_client = cloud_logging.Client(project=project_id)
# logger = logging_client.logger("cloud-event-handler")

# session_service = InMemorySessionService()

# runner = Runner(
#     agent=root_agent, session_service=session_service, app_name="gebu_monitoring_agent"
# )


# async def _parse_cloud_event_request(request: Request) -> tuple[str, str, dict]:
#     """Helper to parse work item ID and payload from JSON or Protobuf CloudEvents."""
#     raw_body = await request.body()
#     content_type = request.headers.get("content-type", "")
#     if "application/json" in content_type:
#         body = json.loads(raw_body)
#         document_name = body.get("value", {}).get("name", "") or body.get(
#             "oldValue", {}
#         ).get("name", "")
#         if not document_name:
#             raise HTTPException(
#                 400, "Could not extract document name from JSON payload."
#             )
#     else:
#         document_name = request.headers.get("ce-subject", "")
#         if not document_name:
#             raise HTTPException(
#                 400, "Could not extract document name from CloudEvent header."
#             )
#         body = {}
#     parts = document_name.split("/")
#     collection_name = parts[-2]
#     work_item_id = parts[-1]
#     return collection_name, work_item_id, body


# @router.post("/cloudevent")
# async def handle_cloudevent(request: Request):
#     """Eventarc HTTP POST push handler for Firestore document creation events."""
#     event_type = request.headers.get("ce-type")
#     if event_type != "google.cloud.firestore.document.v1.created":
#         raise HTTPException(400, "Invalid event type")
#     collection_name, work_item_id, _body = await _parse_cloud_event_request(request)
#     ref = db.collection(collection_name).document(work_item_id)

#     # Idempotency Check
#     doc = ref.get()
#     if doc.exists and doc.to_dict().get("status") == "DONE":
#         return {"status": "skipped", "work_item_id": work_item_id}
#     # Pipeline sub-agent sequence
#     agent_names = ["validation_agent", "enrichment_agent", "notification_agent"]
#     transitions = [{"agent_name": name, "status": "PENDING"} for name in agent_names]

#     try:
#         await session_service.create_session(
#             app_name="gebu_monitoring_agent",
#             user_id="eventarc-user",
#             session_id=work_item_id,
#         )
#     except AlreadyExistsError:
#         logger.log_text(
#             f"Session {work_item_id} already exists, reusing.", severity="INFO"
#         )
#     ref.set(
#         {
#             "status": "PROCESSING",
#             "updated_at": datetime.now(UTC),
#         },
#         merge=True,
#     )

#     # Record initial PENDING states in Firestore
#     set_action_transitions(work_item_id, transitions)

#     # Asynchronous Event Processing & Dynamic Author-Based Transition Updates
#     try:
#         logger.log_text(f"Processing work item: {work_item_id}", severity="INFO")
#         prompt_text = f"Process work item {work_item_id}."
#         final_text = "no output"
#         async for event in runner.run_async(
#             user_id="eventarc-user",
#             session_id=work_item_id,
#             new_message=types.Content(
#                 role="user", parts=[types.Part(text=prompt_text)]
#             ),
#         ):
#             # identifies the active agent using event.author
#             author = getattr(event, "author", None)

#             if author in agent_names:
#                 active_idx = agent_names.index(author)
#                 # Mark current agent and all prior agents in the sequence as SUCCESS
#                 updated = False
#                 for idx in range(active_idx + 1):
#                     if transitions[idx]["status"] != "SUCCESS":
#                         transitions[idx]["status"] = "SUCCESS"
#                         updated = True
#                 if updated:
#                     set_action_transitions(work_item_id, transitions)
#             # Safely extract response text parts
#             if hasattr(event, "content") and event.content and event.content.parts:
#                 for part in event.content.parts:
#                     if hasattr(part, "text") and part.text:
#                         final_text = part.text
#         # Entire pipeline finished cleanly without exception -> Guarantee all marked SUCCESS
#         for t in transitions:
#             t["status"] = "SUCCESS"
#         set_action_transitions(work_item_id, transitions)
#     except Exception as e:
#         # Failsafe cleanup: Mark remaining pending agents as FAILED on exception
#         logger.log_text(f"Pipeline execution failed: {e}", severity="ERROR")
#         for t in transitions:
#             if t["status"] == "PENDING":
#                 t["status"] = "FAILED"
#         set_action_transitions(work_item_id, transitions)
#         ref.update(
#             {
#                 "status": "FAILED",
#                 "error": str(e),
#                 "updated_at": datetime.now(UTC),
#             }
#         )
#         raise HTTPException(status_code=500, detail=str(e)) from e
#     # Store final successful status
#     ref.update(
#         {
#             "status": "DONE",
#             "result": final_text,
#             "updated_at": datetime.now(UTC),
#         }
#     )
#     return {"status": "success", "work_item_id": work_item_id, "result": final_text}

import json
import base64
from datetime import UTC, datetime
from typing import Dict, Any

import google.auth
from fastapi import APIRouter, HTTPException, Request
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.cloud import logging as cloud_logging
from google.genai import types
import sqlalchemy
from sqlalchemy import text
import os

from app.agent import root_agent
from tools.tools import set_action_transitions, engine, DB_SCHEMA

router = APIRouter()

# Clients & Initialization
_, project_id = google.auth.default()
logging_client = cloud_logging.Client(project=project_id)
logger = logging_client.logger("cloud-event-handler")

session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent, session_service=session_service, app_name="gebu_monitoring_agent"
)


async def _parse_pubsub_request(request: Request) -> str:
    """Helper to parse work item ID from a Pub/Sub message payload."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Missing 'message' field in Pub/Sub payload")

    # The data field in Pub/Sub is base64 encoded
    data_b64 = message.get("data")
    if not data_b64:
        raise HTTPException(status_code=400, detail="Missing 'data' field in Pub/Sub message")

    try:
        decoded_data = base64.b64decode(data_b64).decode("utf-8")
        data_json: Dict[str, Any] = json.loads(decoded_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode or parse Pub/Sub data: {e}")

    work_item_id = data_json.get("work_item_id")
    if not work_item_id:
        raise HTTPException(status_code=400, detail="Could not extract 'work_item_id' from Pub/Sub data JSON")

    return work_item_id


def _get_work_item_status(work_item_id: str) -> str | None:
    """Helper to query the current status of a work item from Cloud SQL."""
    with engine.connect() as conn:
        query = text(f"SELECT status FROM {DB_SCHEMA}.work_items WHERE work_item_id = :work_item_id")
        result = conn.execute(query, {"work_item_id": work_item_id}).fetchone()
        if result:
            return result[0]
    return None


def _update_work_item_status(work_item_id: str, status: str, error: str = None, result_text: str = None):
    """Helper to update the status, error, and result of a work item in Cloud SQL."""
    updates = ["status = :status", "updated_at = :updated_at"]
    params = {"work_item_id": work_item_id, "status": status, "updated_at": datetime.now(UTC).isoformat()}
    
    if error is not None:
        updates.append("error = :error")
        params["error"] = error
    if result_text is not None:
        updates.append("result = :result")
        params["result"] = result_text

    set_clause = ", ".join(updates)
    
    with engine.begin() as conn:
        update_query = text(f"UPDATE {DB_SCHEMA}.work_items SET {set_clause} WHERE work_item_id = :work_item_id")
        conn.execute(update_query, params)


@router.post("/cloudevent")
async def handle_pubsub_event(request: Request):
    """HTTP POST push handler for Pub/Sub messages (Cloud SQL inserts)."""
    
    work_item_id = await _parse_pubsub_request(request)

    # Idempotency Check (Check Cloud SQL directly)
    current_status = _get_work_item_status(work_item_id)
    if current_status == "DONE":
        return {"status": "skipped", "work_item_id": work_item_id, "reason": "Already processed"}
    
    if current_status is None:
         raise HTTPException(404, f"Work item {work_item_id} not found in database.")

    # Pipeline sub-agent sequence
    agent_names = ["validation_agent", "enrichment_agent", "notification_agent"]
    transitions = [{"agent_name": name, "status": "PENDING"} for name in agent_names]

    try:
        await session_service.create_session(
            app_name="gebu_monitoring_agent",
            user_id="eventarc-user",
            session_id=work_item_id,
        )
    except AlreadyExistsError:
        logger.log_text(
            f"Session {work_item_id} already exists, reusing.", severity="INFO"
        )
        
    _update_work_item_status(work_item_id, "PROCESSING")

    # Record initial PENDING states in Cloud SQL
    set_action_transitions(work_item_id, transitions)

    # Asynchronous Event Processing & Dynamic Author-Based Transition Updates
    try:
        logger.log_text(f"Processing work item: {work_item_id}", severity="INFO")
        prompt_text = f"Process work item {work_item_id}."
        final_text = "no output"
        async for event in runner.run_async(
            user_id="eventarc-user",
            session_id=work_item_id,
            new_message=types.Content(
                role="user", parts=[types.Part(text=prompt_text)]
            ),
        ):
            # identifies the active agent using event.author
            author = getattr(event, "author", None)

            if author in agent_names:
                active_idx = agent_names.index(author)
                # Mark current agent and all prior agents in the sequence as SUCCESS
                updated = False
                for idx in range(active_idx + 1):
                    if transitions[idx]["status"] != "SUCCESS":
                        transitions[idx]["status"] = "SUCCESS"
                        updated = True
                if updated:
                    set_action_transitions(work_item_id, transitions)
            # Safely extract response text parts
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_text = part.text
                        
        # Entire pipeline finished cleanly without exception -> Guarantee all marked SUCCESS
        for t in transitions:
            t["status"] = "SUCCESS"
        set_action_transitions(work_item_id, transitions)
        
    except Exception as e:
        # Failsafe cleanup: Mark remaining pending agents as FAILED on exception
        logger.log_text(f"Pipeline execution failed: {e}", severity="ERROR")
        for t in transitions:
            if t["status"] == "PENDING":
                t["status"] = "FAILED"
        set_action_transitions(work_item_id, transitions)
        
        _update_work_item_status(work_item_id, "FAILED", error=str(e))
        
        raise HTTPException(status_code=500, detail=str(e)) from e
        
    # Store final successful status
    _update_work_item_status(work_item_id, "DONE", result_text=final_text)
    
    return {"status": "success", "work_item_id": work_item_id, "result": final_text}