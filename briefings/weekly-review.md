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

Read ALL memory files except carry-on:
- people.md
- commitments.md
- life.md
- insights.md
- finances.md (yes, this one too — for quarterly view)
- health.md (same)

## Step 2 — Memory pruning (apply 3-week rule)

For each item in people.md, commitments.md, and life.md:
- When was it last referenced or updated?
- If >3 weeks AND not active: archive it
- If >3 weeks AND vague: ask {{USER_NAME}} via the email if it should stay

Specifically prune:
- People who haven't appeared in any scan in 3+ weeks → move to Archive section in people.md
- "I Said I Would" commitments older than 3 weeks with no movement → flag for the email ("is this still real?")
- Calendar items in life.md that have passed → remove

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

From commitments.md:
- Anything PENDING > 7 days: flag
- Anything CALENDAR NEEDED with no calendar event yet: flag
- Anything OVERDUE: surface loudly

## Step 6 — Insights review

Read insights.md. Any patterns from the past week worth adding? Look at:
- Recurring themes in commitments
- Surprises in calendar (e.g., things that took 3x as long as expected)
- Repeated frustrations or wins

Add at most 1–2 new insights per week. Quality > quantity.

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
5. 🧹 Memory pruning summary (what got archived, what needs your decision)
6. ⏰ Aging commitments (PENDING > 7 days)
7. 🩺 Health this week (the 6 numbers + one pattern + one action — always present)
8. 🧠 New insights added this week
9. 🃏 Wildcard (one contrarian observation about the past week)

Acknowledgment links on action items.

## Step 9 — Update memory

Write the pruning decisions into the files. Update statuses. Move archived items.

## Step 10 — Send

Send email. Confirm.
```

---

## Customization notes

- **Be ruthless with pruning.** The 3-week rule is what keeps the exocortex fast and useful. If memory bloats, output quality degrades.
- **The relationship health check is the highest-leverage section.** Most people lose touch with people they care about not from negligence but from drift. This catches it.
- **The wildcard is required, not optional.** See CLAUDE.md > Wildcard Insight.
