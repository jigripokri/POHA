# Changelog

All notable changes to POHA are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [0.3.0] — 2026-10-25

Memory v2: guardrails against bloat and drift. Six months of production use showed the v0.1 rule ("read everything, update at the end, prune weekly") drifts. Run logs piled into the worklist, insights got rewritten instead of reinforced, pruning depended on someone remembering, and curated files went stale silently. The headline: **memory is now two kinds of files (small curated state and append-only history), and a stdlib Python script enforces the split after every briefing.**

### Added

- **`tools/memory_maint.py`**: memory maintenance in one file, Python 3.9+, stdlib only. `check` (budgets, freshness, schemas, forbidden patterns, missed runs), `rotate` (CHRONIC after 21 days, archive closed rows after 7 days, archive retired insights), `journal-diff` (auto-logs changes a run forgot), `index`, `section`, `lookback`, `journal`, `run-note`, `novelty`, `next-id`, `verify`, and `all`. Never deletes, writes atomically, keeps rolling backups, and never touches `memory/private/`. Exit codes 0/1/2/3/4.
- **`tools/memory_contract.json`**: the single source of truth for per-file budgets, owners, max ages, tags, timezone, the briefing schedule and each briefing's read plan.
- **`tools/tests/`**: 16 unit tests, including a fresh-fork test that runs the shipped templates through a first `all` and expects exit 0 (`python3 -m unittest discover tools/tests`).
- **`memory/INDEX.md`** (generated): staleness markers, budget use, the age of every open commitment, insight caps, missed runs and read plans. Every briefing reads it first.
- **`memory/journal/YYYY-MM.md`**: an append-only event ledger for lookbacks (`memory/journal.md.template` documents the format).
- **`logs/run-notes/YYYY-MM.md`**: per-run operational notes, kept out of memory.
- **`briefings/_memory-contract.md`**: shared Open / During / Close memory rules referenced by every briefing.
- **Lookback recipes** and a **v0.2 upgrade guide** in `docs/memory-system.md`.

### Changed

- **`memory/commitments.md`** is now a worklist only. The 9-column table (`ID | Slug | What | Who | Due | State | Opened | Touched | Note`) uses permanent `C-NNNN` IDs. It has ≤3 pinned projects and a `Closed (last 7 days)` section, and holds no history inside rows.
- **`memory/insights.md`**: ≤25 active lenses, newest first, ≤3 per subject, with permanent `I-NNNN` IDs, evidence counts and retire/supersede metadata.
- Every curated memory template has a line-3 `*Last updated: YYYY-MM-DD (<briefing>)*` header.
- **The 3-week rule is now automatic.** Rows open 21+ days become `CHRONIC`, get one compact line in briefings, and get one Keep / Accept / Reframe question in the weekly review (`EXO_DONE::keep-<slug>` / `accept-<slug>`).
- **All eight briefings** read INDEX first, then only their read plan, journal events through the script, and close with a run note plus `memory_maint.py all`. The evening reflection now makes an insight decision every night (new / evidence / `none — reason`). The weekly review gains a memory-maintenance step and a memory-health line.
- **CLAUDE.md, ARCHITECTURE.md, README.md, SETUP.md and `docs/memory-system.md`** were rewritten around the two-kinds-of-files model.

### Notes

- Python 3.9+ is now a prerequisite. Nothing needs installing beyond the standard library.
- `memory/` and `logs/` stay gitignored. Only `*.template` files and `tools/` ship.
- Upgrading from v0.2 is a one-time guided pass. See "Upgrading from v0.2" in `docs/memory-system.md`. Expect the first `check` on an old tree to report many violations, because that's the drift made visible.

## [0.2.0] — 2026-06-01

Two architecture migrations and the supporting docs/briefings around them. If you're forking or pulling updates, the headline is: **WhatsApp now runs on a native-resolution Go bridge, and health runs on Google Health with a four-surface, cadence-tuned system.**

### Changed

- **WhatsApp bridge: Baileys (TypeScript) → whatsmeow (Go).** The bridge now resolves contact and group-sender names natively, so the old manual phone↔LID juggling is retired.
  - `list_chats` is no longer "broken" — it works *with a name query*; for activity discovery use `search_messages` with broad keywords.
  - Sender names (`chat_name` / `sender_name`) come back populated; only the rare group sender still needs content-based attribution.
  - The late-March-2026 **LID migration is now historically resolved** — storing dual JIDs per contact is no longer required, and there's no "scan both JIDs" step. Priority-DM tables hold a single identity per person.
- **Health data source: Fitbit Web API → Google Health API** (ahead of the Fitbit Web API sunset). Briefings call the Google Health MCP tools **directly** — the Python sync script is retired as a moving part. Substitutable with Whoop / Oura / Apple Health / Garmin via their own connectors.
- **Morning brief health step** is now a conditional, silent-by-default chip — it surfaces only on a deviation from baseline and always implies an action, never dumps numbers.
- **README / SETUP / ARCHITECTURE** updated so the headline data-source stack matches (WhatsApp via native-resolution Go bridge; health via Google Health).

### Added

- **`docs/health-system.md`** — the four health surfaces (conditional morning chip · always-on weekly section · monthly memo · auto-updated `health.md`), the "daily data is noise, signal lives in deviations" cadence principle + table, and the wearable-compliance suppression rule.
- **`briefings/monthly-health.md`** — new 28th-of-the-month, ~250-word Health Memo: vitals trajectory, training load, sleep architecture, optional genetic-context flags, and a twice-yearly pre-bloodwork prep section.
- **Bloodwork reminder** — twice-yearly scheduled nudge the month before each draw, mapping wearable trends to a doctor ask-list.
- **Weekly review health section** — always-present: ~6 numbers + one pattern + one action, from the Google Health weekly summary.
- **Optional genetic-context layer** — if you store *risk priors* (not raw reports) in `health.md`, every health surface cross-references them (e.g. an event-triggered protocol around long-haul flights).
- **Earned-praise / positive-signal system** — the surfaces encourage when things go right, but praise must clear a real bar and stays scarce (≤1 per email); an all-green month pivots the memo from metrics to purpose.
- **WhatsApp bridge durability + liveness** docs — run the bridge as a startup-triggered service so overnight briefings survive a reboot, and assert the bridge is connected + has 24h of traffic before trusting an empty scan.
- **MCP-config-on-packaged-apps** gotcha — sandboxed/packaged desktop clients read a redirected config, not the obvious `%APPDATA%` copy; use the app's "Edit Config" entry point.
- **Step 0.5 health-check protocol** documented end-to-end, including the WhatsApp liveness special case and the non-blocking, noise-suppressed health behavior.

### Notes

- No personal data ships in this repo — all examples are generic and sanitized. `.gitignore` continues to exclude `memory/`.
- Forward-looking items now tracked in `BACKLOG.md`: one-time longitudinal health backfill, and an auto-drafted pre-bloodwork ask-list.

## [0.1.0] — initial release

- Three-layer architecture: Briefing Engine · Memory System · Skills.
- Seven scheduled briefings, five on-demand skills, the acknowledgment loop, and the seven-file memory system.

[0.2.0]: https://github.com/jigripokri/POHA/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jigripokri/POHA/releases/tag/v0.1.0
