summary: Build a provenance-backed knowledge wiki from SEC filings with Claude Managed Agents, check it, ask it questions, and put a small web demo on top.
id: knowledge-wiki-codelab
categories: AI, Agents, Data Engineering
tags: claude, managed-agents, knowledge-wiki, fastapi
status: Draft
authors: Preksha Praveen
Feedback Link: https://github.com/prekshapraveen2502/knowledge-wiki/issues

# Build and query a knowledge wiki with Claude Managed Agents

## Overview

This codelab walks through [my repo](https://github.com/prekshapraveen2502/knowledge-wiki), which holds
Anthropic's knowledge-wiki quickstart (from `anthropics/claude-quickstarts`, MIT license) and a small web
demo on top of it.

The idea, simply: instead of rereading a whole filing cabinet for every question, an agent reads it once and
writes a well-sourced binder. Later questions are answered from the binder.

### What you'll build

- A knowledge wiki: plain markdown pages in a Managed Agents memory store, built from the SEC filings of a
  real take-private deal (Squarespace). Every fact carries its source and the date it was true.
- A small FastAPI page that asks the wiki a question and shows the answer, its sources, and what it cost.

### What you'll learn

- How one Managed Agents session runs a whole multi-agent workflow (extract, resolve, analyze, organize).
- How to check what actually ran, from the platform's own records, instead of trusting an agent's report.
- How to ask the wiki read-only, and how its cost compares with searching the raw documents.
- How to keep a paid run from going wrong: budgets, clean-up, and the mistakes I made.

### What you'll need

- A Mac or Linux machine with Python 3.11 or later.
- An Anthropic API key with Managed Agents access.
- API credit. The build is a paid run: in my run the notebook estimated $25.77 before starting and the
  platform metered $18.86. Have more credit than the budget you set.

## How it works

The notebook does two things.

**Build (once).** One Managed Agents session runs one *dynamic workflow*, described in one message to a lead
agent. The lead agent starts other agents in four phases:

1. **Extract**: one `wiki-extractor` per batch of documents files what the documents say into the wiki.
2. **Resolve**: one `wiki-resolver` works through the wiki's open questions.
3. **Analyze**: one `wiki-analyzer` per batch re-reads it against the wiki and adds what was missed.
4. **Organize**: one `wiki-organizer` tidies the whole wiki and its index.

The phases really are a sequence: each starts only after every agent of the previous one has finished.

**Ask (many times).** Each question opens a fresh session with the wiki mounted **read-only**, so asking can
never change the wiki. The analyst agent may only `read`, `glob` and `grep`.

The files that implement this:

| File | What it does |
| --- | --- |
| `distill_documents_into_knowledge_wiki.ipynb` | The notebook: run it top to bottom |
| `utilities.py` | The notebook's helpers: following a run, checks, costs, clean-up |
| `prompts/` | The agents' instructions |
| `demo/` | My web demo |

## Get the code and set up Python

```bash
git clone https://github.com/prekshapraveen2502/knowledge-wiki.git
cd knowledge-wiki
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c "import anthropic; print(anthropic.__version__)"
```

The last line should print a version starting with `2.` (the requirements pin `anthropic>=2.0.0,<3`).

<aside class="positive">
If you use conda, run <code>conda deactivate</code> first so the venv's Python is the one you get.
</aside>

## Configure keys and settings

Create a file named `.env` in the repo folder. It is in `.gitignore`, so it never gets committed.

```
ANTHROPIC_API_KEY=sk-ant-...
COOKBOOK_BUDGET_USD=30
COOKBOOK_RECORDS_DIR=/full/path/to/a/folder/outside/the/repo
```

- `COOKBOOK_BUDGET_USD` caps the build. It must be at least the estimate the notebook prints, and it should
  be **below your credit balance**, so the budget stops the build before your credit runs out.
- `COOKBOOK_RECORDS_DIR` is where the run's records go. Write the full path: `~` is not expanded. Without it,
  records go to a temporary folder that may be cleared on restart.

The fetch script reads your SEC contact from the shell, not from `.env`:

```bash
export EDGAR_USER_AGENT="Your Name your-email@example.com"
```

## Fetch the filings

```bash
python fetch_data_room.py --tier=core
ls data_room/docs | wc -l
```

You should see 8 documents. Fetching from EDGAR is free; `data_room/` is in `.gitignore`.

I skipped the optional board deck (`fetch_real_deck.py`), since the run recorded in the original notebook
was built without it.

## Run the setup cells

Open the notebook in VS Code (or Jupyter) with the `.venv` kernel. Run cells **one at a time**, not Run All:
Run All would carry straight on into the paid cells.

Run the cells up to, but not including, "The consolidation prompts". These are my run's outputs, so you can
compare:

| Cell | Expected |
| --- | --- |
| Get the documents | `10 documents, 2782 KB text` |
| Normalize PDFs and Word files | `corpus complete: 10 documents` |
| The schema and the wiki's prompts | `environment env_... · wiki store memstore_...` |
| Batch the documents | `10 documents -> 29 files in 25 batches` |

<aside class="negative">
From the schema cell on, the notebook creates things on your Anthropic account and lists them in
<code>created.json</code> in the records folder. Don't restart the kernel from here until the build has
finished: a restart starts a new records folder and a second set of everything.
</aside>

## Check the estimate and the budget

Run the cell under **"The consolidation prompts"**. It prints an estimate, checks it against your budget, and
creates the five agents. My run:

```
Estimated list price $25.77: extraction on claude-haiku-5-5 $9.87 + resolver $0.63, consolidation on claude-haiku-5-5 $12.75 (analyzers) + $2.10 (organizer), lead agent on claude-sonnet-5-5 $0.42. ...
Budget: $30. OK to run, but under twice the estimate: a run that costs more than estimated would stop part-way. Consider raising it.
```

If the budget line doesn't show the number you set, stop: `.env` wasn't saved before the setup cell ran.

<aside class="negative">
Run this cell only once. Each run creates the agents again.
</aside>

## Run the build

Run the cell under **"Describe the goal"** (free: it only prints the message), then the cell under **"Run the
build"**. Keep the machine awake (`caffeinate -i` in another Terminal on a Mac) and don't touch the kernel.

You'll see each phase and thread start. My run ended with:

```
After 30.5 minutes: the agent finished, with no run left open.
The lead agent's report: {"batches_expected": 25, "batches_extracted": 25, ..., "resolved": 10, "unresolvable": 0, "still_open": 294, "batches_analyzed": 25, "organized": true, "index_entries": 219, "failures": []}
```

The parts to check are `batches_extracted` and `batches_analyzed` equal to 25, `organized: true` and an empty
`failures` list. The other counts will differ from run to run.

If the build errors, **don't rerun the cell**: that starts a second paid build. See Troubleshooting.

## Verify the build

An agent's report is only its own claim. The next cells check the platform's records instead.

| Cell | What my run showed |
| --- | --- |
| Build cost by agent | `The session's list cost, as the platform metered it: $18.86 (budget $30)` |
| Check what ran | All 17 checks passed: 52 threads, phases in order, all 25 inputs read by an extractor and by an analyzer, and `Documents no extractor reported filing: none` |
| Read the wiki | `221 memories, 1,257,528 bytes` and `_schema.md is unchanged` |
| File check | stubs, not indexed, indexed missing: all `none`; 1 dangling link; 6 name mismatches |

The 6 name mismatches are files whose front-matter name doesn't match the file name, a slip by the organizer.
The run recorded in the original notebook had none.

## Ask the wiki

Run the cell under **"2. Ask the wiki"** (it creates the analyst agent and defines `ask`), then the four
question cells one at a time. Each costs cents or less. What a right answer does:

| Question | A right answer |
| --- | --- |
| Per-share merger consideration | Leads with $46.50 and gives the path from $44.00 |
| FY2023 adjusted EBITDA | Keeps the reported $235.4M and the ~$252M estimate apart and says they aren't comparable |
| Buyer-side entities | Follows the chain of look-alike names and says only the merger subsidiary merged into the company |
| Revenue for fiscal 2025 | Refuses: "Not in the wiki", because the company was taken private |

Read the answers critically. My buyer answer, for example, listed a founder's surname among the co-investors
even though the question asked for entities only.

## Compare the wiki with the raw documents

The cell under **"What it costs"** asks 6 held-out questions twice: once from the wiki (Haiku) and once by
searching the raw documents (Sonnet). Then run the cost table cell. My run:

| | Mean cost per question |
| --- | --- |
| With the wiki (`claude-haiku-5-5`) | $0.004 |
| Searching the raw documents (`claude-sonnet-5-5`) | $0.058 |

The wiki was cheaper on 6 of 6, by $0.027 to $0.094 per question, so the $18.86 build breaks even after about
349 questions on cost alone. Six questions are a sample, not a benchmark: compare the collapsed answers with
the answer key in the comments of the `BATTERY` list in that cell.

## Clean up and keep the wiki

Run the export cell (it saves every question session's transcript to the records folder), then the clean-up
cell. By default it **keeps the wiki store** and removes everything else:

```
Kept the wiki store: memstore_.... To delete it later: client.beta.memory_stores.delete('memstore_...')
```

Copy that store id: the demo needs it. Afterwards, `created.json` in the records folder should list only the
wiki store.

## Run the web demo

The demo asks the kept wiki from a browser. Each question gets a fresh read-only session, which the app
archives as soon as the answer is in, and interrupts first if it is still running.

```bash
pip install -r demo/requirements.txt
python demo/setup_demo.py
```

`setup_demo.py` creates the demo's own analyst agent and environment (no model runs) and prints two lines. Add
them to `.env` with the store id:

```
WIKI_STORE_ID=memstore_...
DEMO_ENVIRONMENT_ID=env_...
DEMO_AGENT_ID=agent_...
```

It refuses to run a second time once those ids are in `.env`, so it can't make duplicates. Then:

```bash
uvicorn demo.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000, pick one of the example questions, and you'll get the answer with each source shown
as a tag, and the reads, tokens, cost and time below it. The answer is inserted into the page as text, never
as HTML, because it comes from documents an agent read.

When you're done:

```bash
python demo/teardown_demo.py
```

It archives the demo's agent and environment and keeps the wiki.

## Troubleshooting: what went wrong for me

**The build stopped with `billing_error`.** My first two builds ran out of credit partway and left nothing
usable. Have more credit than `COOKBOOK_BUDGET_USD` before starting, and keep the budget below your balance.

**A second set of everything appeared.** Restarting the kernel after the schema cell starts a new records
folder and creates a new environment, store and agents; rerunning the consolidation-prompts cell creates the
agents again. Every records folder's `created.json` lists what that attempt created, so you can archive the
agents, sessions and environments and delete the uploads and stores it lists before trying again.

**An interrupted question left a session open.** The notebook's `ask` has no clean-up of its own, so an
interrupted question's session stays open until the clean-up cell. The demo app closes its sessions in a
`finally` block instead.

## Wrap up

You built a wiki once, checked it against the platform's records, asked it questions read-only, compared its
cost with searching the raw documents, and put a small web page on top.

Further reading: the quickstart's own README (below mine in `README.md`) and `skill.md` cover the other corpus
tiers and building from your own documents.
