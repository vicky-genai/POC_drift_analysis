import pathlib

from dotenv import load_dotenv
from google.adk.agents import SequentialAgent
from google.adk.apps import App
from google.adk.skills import load_skill_from_dir

# import root orchestrator instructions from the prompt
from app.prompt import ROOT_AGENT_INSTRUCTION
from app.sub_agents.gebu_enrichment_agent.enrichment_agent import (
    enrichment_agent,
)
from app.sub_agents.gebu_notification_agent.notification_agent import (
    notification_agent,
)
from app.sub_agents.gebu_validation_agent.validation_agent import (
    validation_agent,
)

env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# import the root skill dynamically from the skills directory
skills_root = pathlib.Path(__file__).resolve().parent.parent / "skills"
root_skill = load_skill_from_dir(skills_root / "root-agent")

# Root Orchestrator
root_agent = SequentialAgent(
    name="gebu_monitoring_agent",
    description=f"{ROOT_AGENT_INSTRUCTION}\n\n{root_skill.instructions}",
    sub_agents=[
        validation_agent,
        enrichment_agent,
        notification_agent,
    ],
)

app = App(
    root_agent=root_agent,
    name="gebu_monitoring_agent",
)
