summary: Build a provenance-backed knowledge wiki with Claude Managed Agents from SEC filings and from photos of AI companies' career-fair brochures, verify it, and ask it questions from a small web app.
id: knowledge-wiki-codelab
categories: data-engineering
tags: claude, managed-agents, knowledge-wiki, fastapi, sec-filings, brochures
status: Published
authors: Preksha Praveen (DAMG 7245, Fall 2026)
feedback link: https://github.com/prekshapraveen2502/knowledge-wiki

# Knowledge wiki with Claude Managed Agents

## Overview
Duration: 3

This codelab walks through [my repo](https://github.com/prekshapraveen2502/knowledge-wiki): Anthropic's
knowledge-wiki quickstart (from `anthropics/claude-quickstarts`, MIT license, see `LICENSE`), run end to end
on the `core` tier, plus a small web app in `demo/` that asks the built wiki questions.

The idea, simply: instead of rereading a whole filing cabinet for every question, an agent reads it once and
writes a well-sourced binder. Later questions are answered from the binder.

The assignment's input is the **images from the in-class hackathon**: 12 photos of AI companies'
career-fair brochures. I first ran the quickstart on its own worked example (a real take-private deal's SEC
filings) to learn it, then built a second wiki from the brochure photos with the same notebook and agents.
The demo app asks the brochure wiki.

What the repo does:

- Turns the brochure photos into text, and fetches the worked example's SEC filings (Squarespace) from EDGAR.
- Has Claude Managed Agents read them once into a wiki: plain markdown pages in a memory store, where every
  fact carries its source and the date it was true, and conflicts between documents stay conflicts.
- Checks the build against the platform's own records, not just the agents' reports.
- Answers questions from the wiki read-only, and compares the cost with searching the raw documents.
- Serves a one-page FastAPI app for asking the wiki.

## Results at a glance
Duration: 3

Every number here comes from the saved outputs of a notebook on main; the notebook section is named for each.

**The brochure run** (`brochures_knowledge_wiki.ipynb`):

| What | Brochure run | Notebook section |
| --- | --- | --- |
| Corpus | 12 documents, 34 KB of text, 1 batch | Batch the documents |
| Build cost, estimated before running | $3.21 | The consolidation prompts |
| Build cost, as the platform metered it | $0.32 (budget $10) | Build cost by agent |
| Build time | 11.6 minutes | Run the build |
| Documents filed / failures | 12 of 12 / none | Run the build |
| Open questions resolved / unresolvable / still open | 1 / 9 / 25 | Run the build |
| Wiki size | 46 files, 70,386 bytes | Read the wiki |

**The worked example** (`distill_documents_into_knowledge_wiki.ipynb`):

| What | My run | Notebook section |
| --- | --- | --- |
| Corpus | 10 documents, 29 files in 25 batches | Batch the documents |
| Build cost, estimated before running | $25.77 | The consolidation prompts |
| Build cost, as the platform metered it | $18.86 (budget $30) | Build cost by agent |
| Build time | 30.5 minutes | Run the build |
| Batches extracted / analyzed | 25 / 25, no failures | Run the build |
| Open questions resolved / unresolvable / still open | 10 / 0 / 294 | Run the build |
| Wiki size | 221 files, 1,257,528 bytes | Read the wiki |
| Checks on the platform's records | 17 of 17 passed, 52 threads | Check what ran |
| Mean cost per question, with the wiki | $0.004 | What it costs |
| Mean cost per question, raw documents | $0.058 | What it costs |
| Break-even on cost alone | about 349 questions | What it costs |

## How it works
Duration: 4

**Build (once).** The notebook uploads the 25 batches and starts one Managed Agents session. A lead agent
runs one *dynamic workflow* in four phases, each starting only after every agent of the previous phase has
finished:

1. **Extract**: one `wiki-extractor` per batch files what the documents say into the wiki.
2. **Resolve**: one `wiki-resolver` works through the wiki's open questions.
3. **Analyze**: one `wiki-analyzer` per batch re-reads it against the wiki and adds what was missed.
4. **Organize**: one `wiki-organizer` tidies the whole wiki and its index.

**Ask (many times).** Each question opens a fresh session with the wiki mounted **read-only**, and the
analyst agent may only `read`, `glob` and `grep`, so asking can never change the wiki.

| File | What it does |
| --- | --- |
| `fetch_data_room.py` | Fetches the filings from EDGAR into `data_room/docs/` (not in Git) |
| `distill_documents_into_knowledge_wiki.ipynb` | Builds, checks and asks the wiki |
| `utilities.py` | The notebook's helpers: following a run, checks, costs, clean-up |
| `prompts/` | The agents' instructions |
| `demo/` | The web app (see The app) |

## Setup and reproduce
Duration: 10

You need Python 3.11 or later, an Anthropic API key with Managed Agents access, and API credit: the build is a
paid run.

```bash
git clone https://github.com/prekshapraveen2502/knowledge-wiki.git
cd knowledge-wiki
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the repo folder (it is in `.gitignore`):

```
ANTHROPIC_API_KEY=sk-ant-...
COOKBOOK_BUDGET_USD=30
COOKBOOK_RECORDS_DIR=/full/path/to/a/folder/outside/the/repo
```

- `COOKBOOK_BUDGET_USD` caps the build. It must be at least the estimate the notebook prints and should be
  **below your credit balance**, so the budget, not your credit, is what stops a run that goes over.
- `COOKBOOK_RECORDS_DIR` must be a full path (`~` is not expanded). Without it, records go to a temporary
  folder that may be cleared on restart.

Fetch the filings (free; the script reads the SEC contact from the shell, not `.env`):

```bash
export EDGAR_USER_AGENT="Your Name your-email@example.com"
python fetch_data_room.py --tier=core
```

Open the notebook with the `.venv` kernel and run cells **one at a time**, not Run All, which would run
straight into the paid cells.

<aside class="negative">
From the schema cell on, the notebook creates things on your Anthropic account and lists them in
<code>created.json</code> in the records folder. Don't restart the kernel until the build has finished: a
restart starts a new records folder and a second set of everything. Run the consolidation-prompts cell only
once: each run creates the agents again.
</aside>

## Build the wiki
Duration: 31

Run the cell under **The consolidation prompts**. It prints the estimate and the budget check, then creates the
five agents. My run printed an estimate of $25.77 against a $30 budget.

Run **Describe the goal** (free: it only prints the message), then **Run the build**. Keep the machine awake and
don't touch the kernel. My run ended:

```
After 30.5 minutes: the agent finished, with no run left open.
```

The lead agent's report is what to check: `batches_extracted` and `batches_analyzed` equal to 25,
`organized: true` and `failures: []`. My other counts (10 resolved, 294 still open, 219 index entries) will
differ from run to run.

<aside class="negative">
If the build errors, don't rerun the cell: that starts a second paid build.
</aside>

## Verify the build
Duration: 5

An agent's report is only its own claim, so the next cells check the platform's records.

| Notebook section | What my run showed |
| --- | --- |
| Build cost by agent | `The session's list cost, as the platform metered it: $18.86 (budget $30)` |
| Check what ran | 17 of 17 checks passed: 52 threads, phases in order, all 25 inputs read by an extractor and by an analyzer; no document went unfiled |
| Read the wiki | 221 memories, 1,257,528 bytes; `_schema.md is unchanged` |
| File check | stubs, not indexed, indexed missing: none; 1 dangling link; 6 name mismatches |

The 6 name mismatches are files whose front-matter name doesn't match the file name, a slip by the organizer.

## Ask the wiki
Duration: 5

Run the cell under **2. Ask the wiki** (it creates the analyst agent), then the four question cells one at a
time. What a right answer does:

| Question | A right answer |
| --- | --- |
| Per-share merger consideration | Leads with $46.50 and gives the path from $44.00 |
| FY2023 adjusted EBITDA | Keeps the reported $235.4M and the ~$252M estimate apart and says they aren't comparable |
| Buyer-side entities | Follows the chain of look-alike names; only the merger subsidiary merged into the company |
| Revenue for fiscal 2025 | Refuses: "Not in the wiki", because the company was taken private |

Read the answers critically. My buyer answer listed a founder's surname among the co-investors even though the
question asked for entities only.

## Wiki versus raw documents
Duration: 4

**What it costs** asks 6 held-out questions twice: from the wiki (`claude-haiku-5-5`) and by searching the raw
documents (`claude-sonnet-5-5`). My run:

| | Mean cost per question |
| --- | --- |
| With the wiki | $0.004 |
| Searching the raw documents | $0.058 |

The wiki was cheaper on 6 of 6, by $0.027 to $0.094 per question, so the $18.86 build breaks even after about
349 questions on cost alone. Six questions are a sample, not a benchmark: the answers are collapsed in that
section, with an answer key in the comments of its `BATTERY` list.

## Clean up
Duration: 2

Run the export cell (it saves each question session's transcript to the records folder), then the clean-up
cell. By default it keeps the wiki store and removes everything else:

```
Kept the wiki store: memstore_.... To delete it later: client.beta.memory_stores.delete('memstore_...')
```

Copy that store id for the app. Afterwards, `created.json` in the records folder lists only the wiki store.

## Build from the brochure images
Duration: 15

The kit's `normalize_any` turns PDFs, Word, Excel, PowerPoint and email into text, but raises on images. So
`brochures/convert_brochures.py` adds the missing piece: for each photo in `brochures/images/` it turns the
photo upright (phones store rotation in EXIF), shrinks it to at most 2000 px, wraps it in a one-page PDF and
sends it through the kit's own `normalize_pdf`, which reads the rendered page, figures included. It writes
`brochures/docs/IMG_xxxx.txt` (not in Git) with a provenance line:

```
[SOURCE: in-class hackathon brochure | file: IMG_4595.JPG | photographed: 2026-10-30 | note: transcribed from a photo]
```

```bash
python brochures/convert_brochures.py
```

Then build with a copy of the notebook, `brochures_knowledge_wiki.ipynb`, pointed at those files:

```
COOKBOOK_DOCS=brochures/docs
COOKBOOK_BUDGET_USD=10
```

`COOKBOOK_DOCS` is the notebook's own switch for your own documents: it skips the worked example's extra files.
Two lines in the copy's schema cell were changed so the extractors aren't told they're reading a Squarespace
deal: the extractor's opening sentence and the store's description. The rest of the prompts is unchanged.

Run the cells as before, up to and including the build checks, then skip to the clean-up cell: the
notebook's question cells and its comparison ask about the Squarespace deal. My brochure run filed 12 of 12
documents with no failures, all checks on the platform's records passed, and the file check found only 2
dangling links, both in the wiki format's own `SKILL.md`.

<aside class="positive">
The worked example's wiki is kept too: switching the app back is a matter of changing
<code>WIKI_STORE_ID</code> and recreating the app's analyst, with no rebuild.
</aside>

## The app
Duration: 5

`demo/app.py` is a FastAPI app with one page that asks the brochure wiki: type a question, or pick one of four
examples (one company in detail, a comparison across companies, a fact across all brochures, and something the
brochures don't say), and get the answer with numbered sources, and the reads, tokens, cost and time below it. Each question gets a
fresh read-only session, which the app archives as soon as the answer is in (interrupting it first if it is
still running). The answer goes into the page as text, never as HTML, because it comes from documents an
agent read.

```bash
pip install -r demo/requirements.txt
python demo/setup_demo.py
```

`setup_demo.py` creates the app's own analyst agent and environment (no model runs) and prints two lines for
`.env`. It refuses to run again once they are there, so it can't make duplicates.

```
WIKI_STORE_ID=memstore_...        # the brochure wiki, printed by the clean-up cell
DEMO_ENVIRONMENT_ID=env_...
DEMO_AGENT_ID=agent_...
```

```bash
uvicorn demo.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. When you're done, `python demo/teardown_demo.py` archives the app's agent and
environment and keeps the wiki.

TODO: app screenshot (codelab/img/app.png). TODO: demo video link.

## Conclusions
Duration: 3

- The brochure wiki cost $0.32 to build from 12 photos and filed every one of them; adding images took one
  small converter and two changed prompt lines; the rest of the kit ran as shipped.
- On the worked example, one build of $18.86 gave a wiki that answered the notebook's questions at a mean of $0.004 each, against
  $0.058 for searching the raw documents.
- Checking the platform's records, not the agents' reports, is what showed each build complete: every input
  read, phases in order, no failures.
- The worked example's wiki is not perfect: 6 name mismatches, 1 dangling link, and an answer that broke an "entities only"
  instruction.

What went wrong for me, so you can avoid it:

- My first two builds ran out of credit partway (`billing_error`) and left nothing usable. Have more credit than
  the budget, and keep the budget below the balance.
- A kernel restart mid-run created a second set of agents, environment and store. Each attempt's
  `created.json` lists what it made, which is what I used to clean up before trying again.
- The notebook's `ask` doesn't close a session if you interrupt it, so the app closes its sessions in a
  `finally` block.
