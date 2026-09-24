import os
import pathlib

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

# import prompt personas from the prompt module
from app.prompt import (
    ENRICHMENT_AGENT_ADDITIONAL_INSTRUCTION,
    ENRICHMENT_AGENT_INSTRUCTION,
    PROMPT_INJECTION_GUARDRAIL,
    SECURITY_GUARDRAILS,
)

# import the storage and log integration tools from the tools module
from tools.tools import (
    fetch_cluster_logs,
    store_incident_enrichment,
    store_incident_summary,
)

env_path = pathlib.Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

skills_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "skills"
enrich_skill = load_skill_from_dir(skills_root / "enrichment-agent")

model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-pro-preview")

# Configuring model-level safety thresholds to OFF
_safety_settings = [
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
]

enrichment_agent = LlmAgent(
    name="enrichment_agent",
    instruction=f"{ENRICHMENT_AGENT_INSTRUCTION}\n\n{ENRICHMENT_AGENT_ADDITIONAL_INSTRUCTION}\n\n{SECURITY_GUARDRAILS}\n\n{PROMPT_INJECTION_GUARDRAIL}",
    model=Gemini(
        model=model_name,
        retry_options=types.HttpRetryOptions(attempts=3),
        config=types.GenerateContentConfig(
            temperature=0.1, safety_settings=_safety_settings
        ),
    ),
    tools=[
        SkillToolset(skills=[enrich_skill]),
        fetch_cluster_logs,
        store_incident_enrichment,
        store_incident_summary,
    ],
    output_key="enrichment_summary",
)
