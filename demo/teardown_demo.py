"""When the demo is over: archive the demo's agent and environment. The wiki store is kept.

Run from the repo folder:  python demo/teardown_demo.py
Then delete the DEMO_AGENT_ID and DEMO_ENVIRONMENT_ID lines from .env.
"""
import os
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
KIT = DEMO.parent
sys.path.insert(0, str(KIT))

import anthropic
from dotenv import load_dotenv

import utilities as kw

load_dotenv(KIT / ".env")
client = anthropic.Anthropic()
agent_id = os.environ.get("DEMO_AGENT_ID")
environment_id = os.environ.get("DEMO_ENVIRONMENT_ID")
if agent_id and kw.remove(f"archive agent {agent_id}", client.beta.agents.archive, agent_id):
    print("archived agent", agent_id)
if environment_id and kw.remove(f"archive environment {environment_id}", client.beta.environments.archive, environment_id):
    print("archived environment", environment_id)
print("Kept the wiki store:", os.environ.get("WIKI_STORE_ID"))
