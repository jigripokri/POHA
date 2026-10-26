# The Memory System

Why plain markdown beats vector databases for personal AI, and why plain markdown still needs a garbage collector.

---

## The architecture in one sentence

Plain markdown, in two kinds of files that never mix: **small curated files** that describe the present (each with a byte budget, an owner and a max age), and **append-only monthly logs** that record what happened. A stdlib Python script enforces the difference after every briefing. Everything stays gitignored.

There is still no database. There is no vector store. There is no RAG. The agent just reads files. It reads fewer of them, and they stay small.

---

## Why plain markdown (unchanged since v0.1)

When this repo started, the default architecture for "personal AI memory" was: embed every input as a vector, store it in a vector DB, retrieve via similarity search, and pass the top-K chunks into context. That's wrong for this problem:

**1. The corpus is small.** A real person's curated state fits comfortably in a context window. There's no retrieval problem if you keep it that way.

**2. Vector search makes you stupid.** Memory retrieval should often be *exact*: what's the status of commitment X? When did I last talk to Y? Vectors are bad at this. Grep is perfect at it.

**3. State has to be auditable.** If the agent gets something wrong about your life, you open the file and fix it in 30 seconds. Try that with a vector DB.

---

## Why v0.3 added rules (what went wrong in production)

The v0.1 rule was "read everything at the start, write back at the end, prune weekly." After six months of real use on a busy life, that drifted in four predictable ways:

1. **One file played two roles.** Every scheduled run appended a "here's what I did" paragraph to `commitments.md`. Within months the worklist was ~80% run log and a very large file, and every briefing paid for it before doing any work. Runs started running out of room, and the optional last step ("add an insight if something surfaced") was the first thing dropped.
2. **Insights had no lifecycle.** The same stuck item generated dozens of near-identical "insights." Numbers got reused. Old entries were cited as "precedent" to justify not acting. New ones went to the bottom where nobody read them, so the file *looked* stale even though it was growing.
3. **The 3-week rule was flagged, not done.** Pruning depended on the weekly review remembering to do it. Week after week, it didn't.
4. **Curated files rotted silently.** "Current quarter" sections still named a quarter from months ago. Nothing said which file was stale, or whose job it was to fix it.

None of this is a model problem. It's a missing-mechanism problem. **The fix is boring on purpose: budgets that are numbers, enforced by a script, not sentences in a prompt.**

---

## The two kinds of files

### Curated state: small, rewritten in place, budgeted

| File | What it is | Budget | Owner · max age |
|------|------------|--------|-----------------|
| `commitments.md` | The worklist: ≤3 pinned projects (current state only) + open rows + `Closed (last 7 days)`. Permanent `C-NNNN` IDs. | 24 KB | weekly · 3 d |
| `insights.md` | ≤25 **active lenses**, ≤3 per subject, newest first. Permanent `I-NNNN` IDs. | 20 KB | weekly · 10 d |
| `people.md` | Relationship context, open threads. | 24 KB | weekly · 28 d |
| `life.md` | Goals, priorities, the current quarter. | 16 KB | weekly · 35 d |
| `finances.md` | Money state. Read only for money questions. | 32 KB | finance · 40 d |
| `health.md` | Health state. Read only for health questions. | 48 KB | health · 40 d |
| `private/carry-on.md` | **Strictly gated.** Never read automatically, never indexed, never touched by the script. | — | — |

Budgets, owners and max ages live in [`tools/memory_contract.json`](../tools/memory_contract.json). Change them there. Add a file there (a per-person file, `weekend-prefs.md`) and the script starts measuring it.

Every curated file carries one header on line 3, updated by whoever changes it:

```
*Last updated: 2026-05-17 (weekly)*
```

That header is the **only** per-run mark a curated file gets. No run notes, no "STATUS <date>" lines, no day counters.

### Append-only history: time-partitioned, never edited

| Path | What it is |
|------|------------|
| `memory/journal/YYYY-MM.md` | **The lookback ledger.** One line per *event* (opened · closed · state · decision · fact · calendar · sent · incident · evidence · insight · review). Steady state ("still open", "Day 46") is not an event and is never written. |
| `logs/run-notes/YYYY-MM.md` | One ≤1,500-char entry per briefing run: result, source health, what it read, what it wrote, its insight decision. Operational, not memory. |
| `memory/archive/**` | Closed commitments by month, retired insights by quarter (full original text), stale sections cut from curated files. Appended by the script. |
| `logs/briefings/YYYY-MM-DD-<briefing>.md` | The content of every sent briefing: "what did the exocortex tell me?" |
| `memory/INDEX.md` | **Generated** after every run (≤6 KB). Read first by every briefing. |

`memory/` and `logs/` are both gitignored. None of this ever reaches GitHub.

---

## The rules that keep it tight

**Read INDEX first, then only what you need.** Each briefing's row in `INDEX > Read plan` says which files it reads in full, which by section (`memory_maint.py section <file> "<heading>"`), and which only by grep. A daily briefing reads tens of KB, not everything. The weekly review is the audit and reads more.

**Transitions are events; steady state is not.** Opening, closing, a state change, a decision, a new fact → one journal line, written through the script so the format can't drift. "Still open, re-verified" → nothing.

**One row per item, forever.** A commitment is edited in place (State, Due, Touched, Note). Closing means setting State and moving the row to `Closed (last 7 days)`; the script archives it a week later.

**CHRONIC is a state, not a nag.** The script flips any row open 21+ days to `CHRONIC`. Chronic rows get one compact line in briefings and one weekly question: **Keep / Accept and stop tracking / Reframe**. This is the 3-week rule, now automatic, and it ends the "flagged for the 11th week" pattern.

**Insights have a lifecycle.**
- A new lens only if the deterministic novelty gate passes (`memory_maint.py novelty …`, exit 0) **and** its subject has fewer than 3 active lenses.
- Same pattern again → `evidence: N+1` + a journal line, never a second entry.
- Retire or supersede by editing the metadata line; the script moves the entry, full text intact, to the quarterly archive.
- The evening decides **every night**: new lens, evidence on an existing one, or `none — <reason>`. Three `none`s in a row is a weekly flag.
- A lens frames thinking and picks a lever. It is never a reason to skip a rule.

**Freshness has an owner.** INDEX marks each curated file 🟠 at 75% of its max age and 🔴 past it. The owner refreshes it, or writes `*Last updated: … (weekly — verified unchanged)*` after actually re-reading it. The weekly review is the enforcement point (`--enforce` turns weekly-owned 🔴 files into violations).

The shared, copy-paste version of these rules for briefings is [`briefings/_memory-contract.md`](../briefings/_memory-contract.md).

---

## `tools/memory_maint.py`

One file, Python 3.9+, stdlib only. Never reads or writes `memory/private/`. Never deletes anything: everything leaves a file by being appended somewhere else first. Every rewrite is atomic and backed up to `logs/maint/backup/<weekday>/`.

| Command | What it does |
|---------|--------------|
| `all --job <briefing>` | The close step of every briefing: check → rotate → journal-diff → index. |
| `check [--enforce]` | Budgets, freshness, schemas (commitments/insights/journal), forbidden patterns (run notes, day counters, STATUS lines), missed runs, private-path references. |
| `rotate` | CHRONIC flips at 21 days, closed rows → monthly archive after 7 days, `status:`-marked lenses → quarterly archive (merging evidence into the survivor). |
| `journal-diff` | Compares the worklist to the last snapshot and writes `(auto)` journal lines for any change a run forgot to log. The ledger stays complete even when a run is sloppy. |
| `index` | Regenerates `memory/INDEX.md`. |
| `section <file> "<heading>"` | Prints one heading's block, so briefings never full-read a big file for one section. |
| `lookback …` | Queries the journal (`--tag`, `--id`, `--event`, `--grep`, `--month`, `--days`; `--archive` and `--run-notes` widen it). |
| `journal …` | Appends one validated journal line. |
| `run-note …` | Appends one run note (refuses a morning/evening/weekly note without an insight decision). |
| `novelty --subject "#tag" --text "…"` | The deterministic near-duplicate gate for a candidate lens (exit 3 = near-duplicate). |
| `next-id C\|I` | Next free commitment or insight ID, reserved for 6 h. |
| `verify` | Line accounting between a file and where its content moved (used when cutting stale sections). |

Exit codes: `0` clean · `1` warnings · `2` violations · `3` novelty near-duplicate · `4` fatal. Tests: `python3 -m unittest discover tools/tests`.

---

## Lookback recipes

```bash
# What was going on with the tracked project in July?
python3 tools/memory_maint.py lookback --tag "#tracked-project" --month 2026-07

# The whole life of one commitment, every event
python3 tools/memory_maint.py lookback --id C-0042

# When did we decide X, and what did we decide?
python3 tools/memory_maint.py lookback --event decision --grep "move" --days 365   # --grep is a case-insensitive regex

# How did the week of May 12–18 go?
python3 tools/memory_maint.py lookback --event review --from 2026-05-12 --to 2026-05-20
python3 tools/memory_maint.py lookback --event closed,opened --from 2026-05-12 --to 2026-05-18 --count

# Did a briefing miss, and what did it read and write that day?
python3 tools/memory_maint.py lookback --run-notes --job evening --from 2026-05-21 --to 2026-05-21

# Pure grep works too, if the script is ever broken
grep -h "· decision ·" memory/journal/*.md
```

---

## What to save vs. not save

**Save it** if it will matter in a week or more: decisions and their reasoning, new facts about people and plans, active deadlines, promises made in either direction, non-obvious patterns (as lenses or evidence). **Save to the journal by default**; promote to a curated file only what describes *current state*.

**Don't save** completed one-off tasks (the journal `closed` line is enough), social chatter, anything re-derivable by re-scanning messages/email/calendar, admin noise, run mechanics (those are run notes), or day counts.

Gut check: *if I needed this in a year, would I want it preserved?* If yes and it's history → journal. If yes and it's "how things are now" → curated file.

---

## Upgrading from v0.2

1. Pull this release and copy the new `tools/` folder in. Set `"adopted"` in `tools/memory_contract.json` to today.
2. **Move run logs out of `commitments.md`.** Any "Evening note / Morning note / ran the brief" paragraphs go to `logs/run-notes/archive/` (cut and paste them; they're history, not memory).
3. **Convert commitments rows** to the 9-column format in `memory/commitments.md.template` (`ID | Slug | What | Who | Due | State | Opened | Touched | Note`). Close or drop anything that's clearly dead; the archive keeps it. Keep the `Note` to current state only.
4. **Restructure insights** into the lens format in `memory/insights.md.template`: newest first, ≤25 active, ≤3 per subject. Fold near-duplicates into one lens with an evidence count. Move the rest, full text, to `memory/archive/insights/YYYY-QN.md` with `status: retired`.
5. Add the line-3 `*Last updated: YYYY-MM-DD (<briefing>)*` header to every curated file.
6. Run `python3 tools/memory_maint.py all --job manual`. Fix every violation it reports; warnings (stale files) are the weekly review's to-do list.
7. Update your scheduled briefings to the versions in `briefings/` (they now reference `briefings/_memory-contract.md`).

Expect the first `check` on an old tree to report many violations. That's the point: it shows you exactly where the drift is.

---

## Failure modes it now catches

- **A briefing writes a run note into a memory file again** → `check` fails (exit 2) at the end of that same run, and the next briefing sees it in INDEX.
- **A row is deleted instead of archived** → `journal-diff` reports "row vanished" and logs an incident line.
- **A briefing stops running** → INDEX's "Missed" line lists every expected slot with no run note; three in a row is a violation.
- **A file nobody owns goes stale** → it turns 🔴 with an owner's name next to it.
- **The same insight keeps getting rewritten** → the novelty gate returns exit 3 and points at the lens to bump instead.

Failure modes it can't catch, so you still should: memory that contradicts a newer input (update it and flag the change), and facts that were never true (fix them by hand, which is the whole point of plain text).

---

## Extension: per-person memory files

For someone who needs ongoing detailed context (a child through a school transition, an aging parent with health complexity, a co-founder), create `memory/<name>.md` and add it to `tools/memory_contract.json` with a budget, an owner and a max age, so it can't silently rot. Suggested sections: Profile · What's current · Recurring themes · History · Open threads (as commitment IDs). Most people need about three.

---

## TL;DR

Plain markdown. Two kinds of files: small curated state and append-only history. Numbers, not adjectives: budgets, owners, max ages. A script enforces them after every run. Read the index first. Log events, not status. One row per item. One lens per pattern.
