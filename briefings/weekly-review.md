# Weekly Review

**Schedule:** `0 9 * * 0` (Sunday 9am)
**Output:** Email to `{{USER_EMAIL}}` with subject `📊 Weekly Review — Week of {{date}}`

Deeper than daily briefings. Prunes memory. Refreshes priorities. Reviews relationships.

---

## Prompt

```
You are running the weekly review for {{USER_NAME}}. This is the most important briefing of the week — it's where the exocortex resets.

## Step 0 — Acknowledgment scan

Standard.

## Step 0.5 — Data source health check

Standard.

## Step 1 — Memory load (all files)

Follow the **Open** steps in [`_memory-contract.md`](./_memory-contract.md): read `memory/INDEX.md` first, then only what this briefing's row in `INDEX > Read plan` marks `full`; everything else by section or grep. The weekly is the audit, so it reads more: memory/INDEX.md, commitments.md, insights.md, people.md and life.md in full; this month's journal; the last 7 days of run notes (`python3 tools/memory_maint.py lookback --run-notes --days 7`); `logs/maint/last-report.md`. finances.md and health.md by section for the quarterly view. Never carry-on.

## Step 2 — Memory maintenance (the audit — do all of it, in order)

The 3-week rule now runs itself: the script flips any row open 21+ days to `CHRONIC`, archives closed rows after 7 days, and moves retired insights to the archive. Your job is the judgment the script can't make.

**2a. Measure.** `python3 tools/memory_maint.py check`. Note every 🔴/🟠 file, every budget >80%, every violation, missed runs, and the count of `insight: none` run notes this week.

**2b. Chronic decisions.** For each CHRONIC row (oldest first, max 5 per week) ask ONE question in the email — **Keep** (`EXO_DONE::keep-<slug>`), **Accept and stop tracking** (`EXO_DONE::accept-<slug>` → State ACCEPTED), or **Reframe** (propose a differently-shaped row, e.g. "book 15 minutes with X" instead of "send the email"; old row SUPERSEDED, new row opened). Apply last week's answers from Step 0.

**2c. Insights curation.** Read insights.md whole. Retire lenses whose `evidence:` hasn't moved in 60 days and no longer change how you'd act (`status: retired`); merge duplicates (`status: superseded · superseded-by: I-…`); decide which three stay for any subject at cap. Never cut/paste between files — the script moves anything with `status:`.

**2d. Freshness (mandatory).** For every weekly-owned file INDEX shows 🔴/🟠: refresh it and update its line-3 header, or write `*Last updated: YYYY-MM-DD (weekly — verified unchanged)*` only if you actually re-read it. Every week: people.md (open threads; drop resolved ones) and life.md (the quarter named must be the *current* quarter; passed calendar items removed). Over budget → move whole stale sections to `memory/archive/stale-sections/YYYY-MM-DD-<file>.md`; never drop a fact that still holds.

**2e. Enforce + record.** `python3 tools/memory_maint.py all --job weekly --enforce` (weekly-owned 🔴 files become violations). Then one `review` journal entry: `python3 tools/memory_maint.py journal --job weekly --ref R-<date>-W --event review --text "Week <Mon D>–<Mon D>" --tags "#review" --block "Scorecard: …\nStory: …\nChronic decisions: …\nMemory: …"`. Scorecard counts come from `lookback --event closed --days 7 --count` and `--event opened`, not from memory.

## Step 3 — Relationship health check

For each Tier 1 person in people.md:
- When was last contact?
- If >2 weeks, flag for the email

For each Tier 2-3 person:
- If >4 weeks, flag for the email

Generate one section: "People you might want to reach out to this week."

## Step 4 — Priority refresh

Re-read life.md.
- Did this past week's calendar reflect the stated priorities? (Be honest.)
- Are this quarter's goals still ON TRACK? Update statuses.
- Are there new themes emerging that should be added?

Generate one section: "Priority alignment check" — was the past week aligned with stated priorities? One paragraph, honest.

## Step 5 — Commitments aging

From `memory/INDEX.md > Commitments aging` (computed — don't recount):
- Due ≤48h and overdue rows: surface loudly
- CALENDAR NEEDED with no event yet: flag
- CHRONIC rows are handled in Step 2b, not here

## Step 6 — Insights review

Read insights.md. Any patterns from the past week worth adding? Look at:
- Recurring themes in commitments
- Surprises in calendar (e.g., things that took 3x as long as expected)
- Repeated frustrations or wins

Add at most 2 new lenses per week, each through the novelty gate (`python3 tools/memory_maint.py novelty …`). A pattern that matches an existing lens is evidence, not a new entry. Quality > quantity.

## Step 6.5 — Weekly health section (always present, if Google Health connected)

Pull the Google Health **weekly summary** directly (no sync script). Unlike the morning chip, this section is **always present** — the weekly is the trend check.

Report ~6 numbers, then one pattern, then one action:

1. Resting HR Δ (vs prior week)
2. Zone-2 minutes vs target
3. Sleep average + variance
4. HRV trend
5. Step consistency (days that hit the floor)
6. Smoothed weight Δ

- **One pattern**: a single observation tying two metrics together ("you sleep 40 min less on nights after evening workouts").
- **One action**: the smallest concrete change for the coming week.
- Six numbers is the cap — don't dump the full panel.
- **Wearable-compliance gate:** if valid-data days < ~80% of the week, skip the numbers and just note low compliance + a wear-the-device nudge.
- Write these into health.md > Wearable data > Weekly trends.

## Step 7 — Next week preview

Look at next week's calendar. Top 3 things that matter. Anything that needs prep this Sunday?

## Step 8 — Compose the email

Subject: 📊 Weekly Review — Week of <date>

Sections:
1. ⚠️ Degraded banner (if any)
2. 🎯 Next week's three (the three things that ACTUALLY matter next week)
3. 👥 People to reach out to (with reason + last contact)
4. 📈 Priority alignment check (one honest paragraph)
5. 🧹 Memory health — one line: `Memory: <n> ✅ · <n> 🟠 · <n> 🔴 (<names>) · commitments <KB>/24 · insights <active>/25 · runs <seen>/<expected>` — plus the CHRONIC Keep / Accept / Reframe questions
6. ⏰ Aging commitments (PENDING > 7 days)
7. 🩺 Health this week (the 6 numbers + one pattern + one action — always present)
8. 🧠 New insights added this week
9. 🃏 Wildcard (one contrarian observation about the past week)

Acknowledgment links on action items.

## Step 9 — Update memory

Done in Step 2 (rows edited in place, lenses retired by metadata, the script moves what's archived). No "Weekly Review — <date>" blocks in any memory file — the `review` journal entry is the record.

Then the **Close** steps in [`_memory-contract.md`](./_memory-contract.md): save the briefing, update line-3 headers, `memory_maint.py run-note`, `memory_maint.py all --job weekly`.

## Step 10 — Send

Send email. Confirm.
```

---

## Customization notes

- **Be ruthless with the chronic list.** Keep / Accept / Reframe is what keeps the exocortex fast and useful. Accepting an item you'll never do is a win, not a failure. Budgets in `tools/memory_contract.json` are the hard backstop. If memory bloats, output quality degrades.
- **The relationship health check is the highest-leverage section.** Most people lose touch with people they care about not from negligence but from drift. This catches it.
- **The wildcard is required, not optional.** See CLAUDE.md > Wildcard Insight.
