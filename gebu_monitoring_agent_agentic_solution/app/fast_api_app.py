import os

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from app.cloud_event_handler import router as cloudevent_router

# CONFIG
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

artifact_service_uri = None
session_service_uri = None

# ADK APP
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    session_service_uri=session_service_uri,
)

app.title = "gebu_monitoring_agent"

# Eventarc router
app.include_router(cloudevent_router)


@app.get("/health")
def health():
    return {"status": "ok"}
