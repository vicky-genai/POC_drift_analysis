import os
import pathlib

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

# import prompt personas from the prompt module at root level
from app.prompt import (
    PROMPT_INJECTION_GUARDRAIL,
    SECURITY_GUARDRAILS,
    VALIDATION_AGENT_INSTRUCTION,
)

# import custom verification tool
from tools.tools import validate_work_item

env_path = pathlib.Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

skills_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "skills"
val_skill = load_skill_from_dir(skills_root / "validation-agent")

model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-pro-preview")

# Configuring model-level safety thresholds to OFF
_safety_settings = [
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
]

_gemini_model = Gemini(
    model=model_name,
    retry_options=types.HttpRetryOptions(attempts=3),
    config=types.GenerateContentConfig(safety_settings=_safety_settings),
)

val_toolset = SkillToolset(skills=[val_skill])

validation_agent = LlmAgent(
    name="validation_agent",
    instruction=f"{VALIDATION_AGENT_INSTRUCTION}\n\n{SECURITY_GUARDRAILS}\n\n{PROMPT_INJECTION_GUARDRAIL}",
    model=_gemini_model,
    tools=[val_toolset, validate_work_item],
    output_key="validation_data",
)
