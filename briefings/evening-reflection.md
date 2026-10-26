# Evening Reflection

**Schedule:** `0 21 * * *` (9pm daily)
**Output:** Email to `{{USER_EMAIL}}` with subject `🌙 Evening Reflection — {{date}}`

Lighter than the morning brief. Catches plans confirmed after 5am. Reflects on the day. Updates memory.

---

## Prompt

```
You are running the evening reflection for {{USER_NAME}}. Follow this recipe.

## Step 0 — Acknowledgment scan (same as morning)

Search Gmail for EXO_DONE signals received since the morning brief.
Match each slug to the `Slug` column of commitments.md → State DONE, move to Closed, one journal `closed` line. Archive signals.

## Step 0.5 — Data source health check

Same as morning. Surface degraded banner if needed.

## Step 1 — Memory load

Follow the **Open** steps in [`_memory-contract.md`](./_memory-contract.md): read `memory/INDEX.md` first, then only what this briefing's row in `INDEX > Read plan` marks `full`; everything else by section or grep. For this briefing: memory/INDEX.md, memory/commitments.md and memory/insights.md in full (insights is capped at ~20 KB, and the insight decision below needs the active set); today's journal (`python3 tools/memory_maint.py lookback --days 0`); people and life by section/grep only.

## Step 2 — Late-day plan confirmations

Re-scan WhatsApp groups + DMs for activity since 5am.
Focus on: plan confirmations ("works", "see you Sat", "done"), new commitments, anything that should have been on the morning brief but wasn't.

## Step 3 — SMS sweep (lighter)

Via Chrome → messages.google.com. Only SMS-primary contacts (from CLAUDE.md > Messaging Platform Rules).
Any plans confirmed? Any unanswered to you?

## Step 4 — Calendar tomorrow

Brief look at tomorrow's calendar. Anything that needs prep tonight?

## Step 5 — Today's reflection

Look at:
- Commitments completed today (from Step 0)
- Calendar events that happened
- Any patterns worth noting

Generate one paragraph: "What actually happened today?" Honest, brief, not flattering.

## Step 6 — Compose the email

Subject: 🌙 Evening Reflection — <day, date>

Sections:
1. ⚠️ Degraded banner (if any)
2. 📅 Tomorrow morning (top 3 things on the calendar, with prep notes if needed)
3. 💬 Late-day confirmations (plans confirmed after 5am, with calendar suggestions)
4. ✅ Today's wins (what actually got done)
5. 🤔 Reflection (one paragraph, honest)
6. 🧠 Insight — always present: the human-voice version of the Step 7 insight decision (a new lens, an existing lens applied to today, or one honest line on why nothing new surfaced and what that says). No insight IDs in the email.

Include `mailto:` acknowledgment links on any new action items.

## Step 7 — Memory update

**7a. Worklist.** Close what got done, open what you found (`next-id C`), edit Notes that changed. No history, no day counts. CHRONIC rows untouched unless a real fact changed.

**7b. Journal.** ≤8 lines via `memory_maint.py journal`: every open/close/state change, decisions made today, facts worth recalling in a year.

**7c. People.** Core-family facts only (≤400 chars) into people.md; everything else is a journal `fact` line. life.md is the weekly's job.

**7d. Insight decision — mandatory, exactly one of three, every night.** Write the candidate (title ≤110 chars + body ≤600 chars ending in `Lens: …`, one primary subject tag). Then run `python3 tools/memory_maint.py novelty --subject "#tag" --text "<title>. <body>"`:
- exit **3** (near-duplicate of a named lens) → **(b) evidence:** bump that lens's `evidence:`, journal `--event evidence --ref I-NNNN`.
- exit **0**, prints `SUBJECT AT CAP` → (b) if one of the three already covers it; otherwise mark the weakest `status: superseded · superseded-by: I-<new>` and do (a).
- exit **0**, subject below cap → **(a) new lens:** `next-id I`, insert at the top of `## Active` in the exact format, journal `--event insight`.
- **(c) none** only when the day produced no pattern and no instance of an existing one: put `none — <reason>` in the run note. Three `none` evenings in a row is a weekly-review flag.

Then the **Close** steps in [`_memory-contract.md`](./_memory-contract.md): save the briefing, update line-3 headers, `memory_maint.py run-note`, `memory_maint.py all --job evening`. The run note's `--insight` must be `new I-NNNN`, `evidence I-NNNN` or `none — <reason>` — the script refuses anything else.

## Step 8 — Send

Send email. Confirm.
```

---

## Customization notes

- **Tone:** lighter than morning. The morning brief is operational; evening is reflective.
- **Don't repeat the morning's content.** If something was on the morning brief and didn't move, don't re-list it. Only surface deltas.
- **Reflection paragraph is for you, not for performance.** Brutal honesty serves the exocortex better than self-congratulation.
