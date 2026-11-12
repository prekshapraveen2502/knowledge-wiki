"""Demo web app: ask the kept knowledge wiki a question and see the sourced answer and its cost.

Run from the repo folder:  uvicorn demo.app:app --host 127.0.0.1 --port 8000
then open http://127.0.0.1:8000 . Needs WIKI_STORE_ID, DEMO_ENVIRONMENT_ID and DEMO_AGENT_ID in .env
(python demo/setup_demo.py prints the last two).

Each question gets a fresh session with the wiki mounted read-only, as the notebook's ask() does, and the
session is archived when the answer is in, so a question can't change the wiki and no session is left open.
"""
import os
import sys
import time
from pathlib import Path

DEMO = Path(__file__).resolve().parent
KIT = DEMO.parent
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(DEMO))

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import demo_config as cfg
import utilities as kw

load_dotenv(KIT / ".env")
STORE_ID = os.environ["WIKI_STORE_ID"]
ENVIRONMENT_ID = os.environ["DEMO_ENVIRONMENT_ID"]
AGENT_ID = os.environ["DEMO_AGENT_ID"]

MAX_QUESTION_CHARS = 1000
ANSWER_TIMEOUT_S = 600  # the notebook allows an hour; a wiki answer takes far less

client = anthropic.Anthropic()
AGENT_VERSION = client.beta.agents.retrieve(AGENT_ID).version

app = FastAPI(title="Deal knowledge wiki demo")


class Question(BaseModel):
    question: str


def close_session(session_id):
    """Stop the session if it is still running, then archive it. Returns whether it was archived."""
    try:
        if client.beta.sessions.retrieve(session_id).status != "idle":
            client.beta.sessions.events.send(session_id=session_id, events=[{"type": "user.interrupt"}])
        kw.wait_for_idle_status(client, session_id)
    except Exception as exc:  # still archive below if we can; report what happened
        print(f"session {session_id}: could not confirm idle: {exc}")
    return kw.remove(f"archive session {session_id}", client.beta.sessions.archive, session_id)


def answer_question(question):
    """One fresh read-only session per question, as the notebook's ask(); returns the answer and its cost."""
    started = time.time()
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": AGENT_ID, "version": AGENT_VERSION},
        environment_id=ENVIRONMENT_ID,
        title=question[:60],
        resources=[
            {
                "type": "memory_store",
                "memory_store_id": STORE_ID,
                "access": "read_only",
                "instructions": cfg.WIKI_INSTRUCTIONS,
            }
        ],
        budget=kw.budget(cfg.QUERY_BUDGET_USD),
    )
    stats = {"session_id": session.id, "model": cfg.QUERY_MODEL, "question": question}
    reply = []
    try:
        sent = client.beta.sessions.events.send(
            session_id=session.id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": question}]}],
        )
        sent_id = sent.data[0].id if getattr(sent, "data", None) else None
        try:
            stats["outcome"] = kw.poll_until_end_turn(
                client, session.id, poll_s=2.0, timeout_s=ANSWER_TIMEOUT_S, sink=reply, stats=stats, after=sent_id
            )
        except TimeoutError:
            stats["outcome"] = "timeout"
    finally:
        archived = close_session(session.id)
    stats["list_usd"] = kw.list_usd(client.beta.sessions.retrieve(session.id).usage)
    start = stats.get("answer_from", 0)
    answer = "\n\n".join(reply[start:]) or "\n\n".join(reply)
    outcome = stats["outcome"]
    return {
        "answer": answer,
        "outcome": outcome,
        "outcome_note": None if outcome == "end_turn" else kw.OUTCOMES.get(outcome, f"the turn ended: {outcome}"),
        "reads_searches": stats.get("reads_searches", 0),
        "tokens_in": stats.get("tokens_in", 0),
        "priced_usd": round(kw.question_usd(stats), 5),
        "list_usd": stats["list_usd"],
        "seconds": round(time.time() - started),
        "session_id": session.id,
        "session_archived": archived,
    }


@app.get("/")
def page():
    return FileResponse(DEMO / "index.html")


@app.post("/ask")
def ask(body: Question):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Type a question first.")
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(status_code=400, detail=f"Keep the question under {MAX_QUESTION_CHARS} characters.")
    try:
        return answer_question(question)
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail=f"The API call failed: {exc}") from exc
