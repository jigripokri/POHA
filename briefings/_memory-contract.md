# Memory Contract (shared by every briefing)

> Every briefing in `briefings/` says **"Follow `briefings/_memory-contract.md`"** at its memory steps. This file is the single place the read/write rules live, so the eight briefings can't drift apart. Full rationale: [`docs/memory-system.md`](../docs/memory-system.md).
>
> Run every command from the repo root (the folder with `CLAUDE.md`). Requires Python 3.9+; stdlib only.

---

## Open (before any scan)

1. **Read `memory/INDEX.md` in full.** It is generated after every run and tells you what exists, what is stale (🟠/🔴), what is over budget, the **age of every open commitment** (use these day counts — never compute or write your own "Day N"), which insight subjects are at their cap, and which briefings missed a run.
2. **Read in full only what your briefing's row in `INDEX > Read plan` marks `full`.** For `§` entries run `python3 tools/memory_maint.py section <file> "<heading>"` (prints one heading's block). For `q` entries grep first (`python3 tools/memory_maint.py lookback --tag "#tag" --days 30`, or `grep -n`), then any search index you have. Never full-read a `q` or `—` file. Never open `memory/private/`.
3. If `memory/INDEX.md` is missing or more than 36 h old, run `python3 tools/memory_maint.py index` first. If the script itself fails, carry on with the files you need and put `⚠️ DEGRADED: memory tools` in the email. Never block the briefing on memory tooling.

## During the run

- **Worklist.** Edit rows in place in `memory/commitments.md` (`ID | Slug | What | Who | Due | State | Opened | Touched | Note`). New row → ID from `python3 tools/memory_maint.py next-id C`, Opened = Touched = today, `Note` ≤160 chars of current state. Never add a second row for the same item. Closing = set State (DONE / DROPPED / MOOT / ACCEPTED / SUPERSEDED), Touched = today, move the row to `## Closed (last 7 days)`. **No history inside rows, no day counts, no "STATUS <date>" lines, no run notes** — the script rejects them.
- **Acknowledgments.** `EXO_DONE::<slug>` matches the `Slug` column exactly first, then fuzzy on `What` → State DONE, move to Closed, one journal `closed` line. `EXO_DONE::keep-<slug>` keeps a CHRONIC row (Touched = today); `EXO_DONE::accept-<slug>` → State ACCEPTED, move to Closed, journal `closed` line.
- **CHRONIC rows** (State = CHRONIC, set by the script after 21 days open): one compact line in the email (`Chronic (N): … · …` with Done links). No prose, no routing, no journal line, no insight — unless a real new fact arrived.
- **Journal.** Every transition you cause or observe gets **one line, via the script** (it validates format, date heading and tags):
  `python3 tools/memory_maint.py journal --job <briefing> --ref <C-/I-/ref or —> --event <opened|closed|state|decision|fact|calendar|sent|incident|evidence|insight> --text "<≤200 chars>" --tags "#tag #tag"`
  Tags come from `tools/memory_contract.json > tags`. "Still open", "re-verified" and "no movement" are not events — write nothing for them. Keep to your briefing's cap (morning/evening ≤8 lines, weekly ≤12 + one review block, others ≤4).
- **Insights** follow the lifecycle in `memory/insights.md`: the novelty gate before any new lens, `evidence: N+1` for a repeat, ≤3 active per subject. Only the evening (every night) and the weekly create lenses; everyone else only adds evidence.
- Nothing from `memory/private/` ever goes into a journal line, run note, INDEX, email or external call.

## Close (after the email is sent — never block the send on this)

1. Save the email content as `logs/briefings/YYYY-MM-DD-<briefing>.md` (path set by `briefing_archive` in `tools/memory_contract.json`; `logs/` is gitignored). It's the "what did the exocortex tell me?" record, and the run note checks it exists.
2. Update line 3 (`*Last updated: YYYY-MM-DD (<briefing>)*`) of every memory file you changed.
3. Append the run note. Run notes are operational logs, not memory — "followed the brief, sources UP" never goes into a memory file again:
   `python3 tools/memory_maint.py run-note --job <briefing> --result "<sent|draft|failed|skipped> (<what>)" --health "<one line>" --read "<one line>" --wrote "<one line>" --insight "<new I-NNNN | evidence I-NNNN | none — reason>" --note "<≤400 chars>"`
4. Run `python3 tools/memory_maint.py all --job <briefing>` (= check + rotate + journal-diff + index). Exit 0/1 → done. Exit 2 → read `logs/maint/last-report.md`, fix anything caused by *your* writes this run, run it once more; still 2 → leave it for the weekly and say `maint: exit 2 (<first violation>)` in your final message. Exit 4 → stop and report the error; don't retry.
