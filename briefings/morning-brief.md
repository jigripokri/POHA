# Morning Brief

**Schedule:** `0 5 * * *` (5am daily)
**Output:** Email to `{{USER_EMAIL}}` with subject `🌅 Morning Brief — {{date}}`

The big one. Full sweep of all inputs. Lands before the alarm.

---

## Prompt

```
You are running the daily morning brief for {{USER_NAME}}. Follow this recipe exactly.

## Step 0 — Acknowledgment scan

Search Gmail for emails with subject starting `EXO_DONE` received in the last 36 hours.
For each match:
- Extract the slug after `EXO_DONE::`
- Open memory/commitments.md
- Find the matching row (exact match on the `Slug` column, then fuzzy on `What`)
- Set State DONE, Touched = today, move the row to `Closed (last 7 days)`, write one journal `closed` line
- `EXO_DONE::keep-<slug>` / `accept-<slug>` are answers to the weekly CHRONIC question (see `_memory-contract.md`)
- Archive the signal email
- If no match found, note it for the email's "Loose Ends" section

## Step 0.5 — Data source health check

Ping each data source in parallel with a minimal read. Record UP/DOWN.
Sources: Gmail, Calendar, Tasks, WhatsApp, Android Messages (if connected), Google Health (if connected — connection-status / profile ping), Monarch (if connected).
If any source is DOWN, surface a `⚠️ DEGRADED: <source>` banner at the top of the email.
NEVER block the briefing on a degraded source — proceed with what's available.

WhatsApp bridge-liveness assertion (critical — an empty scan can be a dead bridge, not a quiet day):
- Confirm the bridge reports a connected/registered session.
- Confirm the store has received at least one message (any chat) in the last 24h.
- If either fails, treat "no WhatsApp activity" as a probable bridge-down signal → flag `⚠️ DEGRADED: WhatsApp` and say so plainly. Do NOT report a "quiet morning."

Google Health is the lowest-priority source — never block or delay the brief on it. A single down-day is silent; only raise `⚠️ DEGRADED: health` after multiple consecutive down-days.

## Step 1 — Memory load

Follow the **Open** steps in [`_memory-contract.md`](./_memory-contract.md): read `memory/INDEX.md` first, then only what this briefing's row in `INDEX > Read plan` marks `full`; everything else by section or grep. For this briefing:
1. memory/INDEX.md (full — commitment ages, staleness, missed runs)
2. memory/commitments.md (full — the worklist)
3. memory/people.md → `python3 tools/memory_maint.py section memory/people.md "<your core-family heading>"`; other people by grep when they surface
4. memory/insights.md → grep by subject tag only when writing the Insight section (`grep -n "subject: #tag" memory/insights.md`)
5. Yesterday + today in the journal: `python3 tools/memory_maint.py lookback --days 1`

DO NOT read memory/private/carry-on.md.

## Step 2 — Calendar scan

Read Google Calendar for the next 24 hours.
Flag: anything before 9am, anything stacked (back-to-back without buffer), anything that conflicts with a recurring block in life.md.
If a "tracked project" event is scheduled, surface it explicitly.

## Step 3 — Inbox scan (Gmail)

Search Gmail for: unread emails in the last 24h, prioritized by tier.
Apply tier weights from CLAUDE.md.
Bucket into:
- 🔥 NEEDS REPLY TODAY (urgent + from someone in tier 1-2)
- 📥 NEEDS REPLY THIS WEEK
- ⏳ FYI (don't surface unless interesting)

## Step 4 — WhatsApp group sweep

For each priority group in CLAUDE.md > Priority WhatsApp Groups, call list_messages with limit 30, parallelize.
Filter for:
- @ mentions of {{USER_NAME}}
- Direct questions ("anyone want to...", "who's coming...")
- Plan-making language ("Saturday", "tomorrow", "let's", "RSVPs")
- Time-sensitive commitments

Bucket as ON YOU (you need to act) vs FYI.

## Step 5 — DM sweep (active chat discovery)

Run search_messages with 6 broad keywords in parallel: "ok", "thanks", "tomorrow", "haha", "please", "yes".
Each with limit 20.
Extract unique chat_jid values from messages in the last 24-48h.
Filter to DMs only (exclude @g.us group JIDs and known bot chats).
For each discovered active DM, call list_messages with limit 10.
Apply commitment detection heuristics (see CLAUDE.md > DM Commitment Sweep).
Detect: unanswered messages to you, confirmed plans, promises you made.

## Step 6 — SMS sweep (if Android Messages connected)

Via Chrome navigate to messages.google.com. Read or screenshot inbox.
Scan any SMS threads with activity in last 24h.
Primary targets: people listed in CLAUDE.md as SMS-primary (often spouse/sibling).

## Step 7 — Tasks check (via Chrome)

Navigate to tasks.google.com.
For each task list flagged "primary" in CLAUDE.md, read open tasks.
Surface anything overdue or due today.

## Step 8 — Health chip (if Google Health connected) — CONDITIONAL & SILENT BY DEFAULT

Pull yesterday's daily summary directly from the Google Health MCP (daily summary / rollup). NO sync script — call the tools directly.

This chip is **omitted entirely on a normal day.** Compute the deviation triggers and only surface a line if one trips:

- Sleep below floor (e.g. < 6h, or a sleep-score collapse)
- Resting HR > baseline + ~5 bpm (from health.md)
- HRV down meaningfully vs the 7-day average
- Multiple consecutive days of zero Zone-2 minutes
- Weight spike outside normal day-to-day variance

Rules when a trigger fires:
- **Never dump numbers.** State the deviation in one plain line and imply the action. Plain language, never doctor-speak. ("Resting HR is running 6 bpm high for the third day — you're either fighting something off or under-slept. Skip the hard session.")
- **Wearable-compliance gate:** if valid-data days are below ~80% of the week, SUPPRESS all triggers (the data's unreliable) and instead, at most, a one-line nudge to wear the device. A trend from three data points is worse than no trend.
- **Genetic-context flags:** if health.md stores genetic risk priors, cross-reference them here (e.g. a clotting-risk prior + a long-haul flight on today's calendar → surface the relevant protocol). See [`docs/health-system.md`](../docs/health-system.md).
- **Earned praise (scarce):** only if a real bar is cleared (streak milestone, target hit, sustained good trend) may you surface ONE praise line naming the specific behavior + payoff. Otherwise no praise. Never both an alert and praise in the same brief.

Always write the latest daily snapshot into health.md > Wearable data > Latest daily, even when nothing surfaces in the email.

## Step 9 — Compose the email

Format:

Subject: 🌅 Morning Brief — <day, date>

Body sections, in this order:
1. ⚠️ Degraded banner (if any)
2. 🎯 Today's three (the three things that ACTUALLY matter today — your call, based on everything above)
3. 🔴 #1 Tracked project update (from CLAUDE.md)
4. 📞 People to reach out to (with reason + tier)
5. 📥 Inbox (NEEDS REPLY TODAY items)
6. 💬 Group chat (ON YOU items only)
7. 💌 DMs (unanswered + commitments detected)
8. 📅 Calendar today (events with prep notes)
9. ✅ Open commitments aging (>3 days)
10. 🩺 Health chip (ONLY if a Step 8 trigger fired — omit this section entirely otherwise)
11. 🧠 Insight (one wildcard observation from the data — see CLAUDE.md > Wildcard Insight)

For EVERY action item, include a `mailto:` acknowledgment link:
`<a href="mailto:{{USER_EMAIL}}?subject=EXO_DONE%3A%3A<slug>">✅ I did this</a>`

Slug rules: lowercase, hyphens, max 40 chars, derived from item title.

## Step 10 — Update memory

- New commitment → one new row in commitments.md (`next-id C`, State `CALENDAR NEEDED` or `PENDING`) + one journal `opened` line.
- Closed, changed or decided → edit the row in place + one journal line. CHRONIC rows get one compact line in the email, nothing else.
- People: core-family facts only into people.md (≤400 chars); everything else about people is a journal `fact` line.
- Insights: the morning never creates a lens. If today's Insight section is an instance of an active lens, write it fresh (no IDs in the email) and bump that lens's `evidence:` + one journal `evidence` line.
- Journal cap: 8 lines. "Still open" is not an event.

Then the **Close** steps in [`_memory-contract.md`](./_memory-contract.md): save the briefing, update line-3 headers, `memory_maint.py run-note`, `memory_maint.py all --job morning`.

## Step 11 — Send

Send the email from {{USER_EMAIL}} to {{USER_EMAIL}} (self).

Done. Confirm completion with: "Morning brief sent. <N> action items. <M> commitments updated."
```

---

## Customization notes

- **Length budget:** if the email runs longer than 1200 words, you're surfacing noise. Tighten the filters in Steps 3–5.
- **Wake-up time:** schedule should be 60–90 min before your alarm.
- **Tier weights:** edit CLAUDE.md > Priority Tiers, not this prompt.
- **The "🎯 Today's three" section is the most important.** Three things, ranked. Spend the most reasoning budget here.
