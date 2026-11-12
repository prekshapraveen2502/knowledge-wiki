"""One-time setup: create the environment and the analyst agent the demo app uses.

Run once from the repo folder:  python demo/setup_demo.py
It runs no model. It prints two lines to add to .env.
"""
import os
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
KIT = DEMO.parent
sys.path.insert(0, str(DEMO))

import anthropic
from dotenv import load_dotenv

import demo_config as cfg

load_dotenv(KIT / ".env")
if os.environ.get("DEMO_AGENT_ID") or os.environ.get("DEMO_ENVIRONMENT_ID"):
    sys.exit("DEMO_AGENT_ID or DEMO_ENVIRONMENT_ID is already in .env; not creating a second set.")

client = anthropic.Anthropic()
environment = client.beta.environments.create(name="deal-wiki-demo", config=cfg.ENVIRONMENT_CONFIG)
print("created environment", environment.id)
agent = client.beta.agents.create(
    name="deal-analyst-demo",
    model=cfg.QUERY_MODEL,
    system=cfg.ANALYST_SYSTEM,
    metadata=cfg.TAG,
    tools=cfg.READER_TOOLS,
)
print("created agent", agent.id, "version", agent.version)
print("\nAdd these two lines to .env:")
print(f"DEMO_ENVIRONMENT_ID={environment.id}")
print(f"DEMO_AGENT_ID={agent.id}")
