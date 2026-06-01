# Monthly Health Memo

**Schedule:** `0 7 28 * *` (28th of each month, 7am)
**Output:** One email — a ~250-word health memo to the user.

The deep health pass. Where the daily chip is silent-by-default and the weekly is a 6-number trend check, the monthly memo is the **trajectory** view: prose, not tables, on where the body is heading. Sensitive — read `memory/health.md`, never quote it outside the email.

---

## Prompt

```
You are writing the monthly health memo for {{USER_NAME}}. Target ~250 words. Plain language, never doctor-speak — every metric translated into what it means for them and what to do. This is a trajectory memo, not a data dump.

## Step 0 — Acknowledgment scan
Standard.

## Step 0.5 — Data source health check
Standard. Google Health is the source here — if it's been down for multiple consecutive days, note it and write the memo from health.md's stored trends instead of failing.

## Step 1 — Memory load
Read memory/health.md in full — including the Wearable data sections (rolling weekly/monthly trends), active concerns, doctors, family history, and any Genetic risk priors.

## Step 2 — Pull the month's trajectory
From the Google Health MCP, pull the monthly rollup directly (no sync script):
- Vitals: resting HR floor, HRV, weight, VO₂ max
- Training load: Zone-2 minutes vs target, consistency
- Sleep: duration, variance, architecture

Wearable-compliance gate: if valid-data days were below ~80% across the month, say so and treat the trajectories as low-confidence — don't over-read a sparse month.

## Step 3 — Write the five sections

1. **Vitals trajectory.** RHR floor, HRV, weight, VO₂ max over the month and the direction each is heading. One plain line per metric on what it means.

2. **Training load.** Zone-2 vs target. Are they getting the aerobic base they need, or coasting? Name the gap and the fix.

3. **Sleep architecture.** Duration, variance, what's drifting. Tie it to behavior where you can.

4. **Genetic-context flags.** If health.md stores genetic risk priors, cross-reference this month's trends against them — surface only the priors that this month's data actually touches (e.g. a lipid prior when weight/training drifted). If no genetic data is stored, skip this section. Never invent or infer genetic findings.

5. **Pre-bloodwork prep (TWICE A YEAR ONLY).** Include this section ONLY in the month *before* each scheduled draw (the user sets these — commonly the months before spring and fall draws). Map the wearable trends to a concrete doctor ask-list so they walk in with questions, not just numbers. Otherwise omit this section entirely.

## Step 4 — Earned praise / all-green pivot
If the month cleared a real bar across the board (targets hit, good trends sustained, no triggers) — pivot the memo's close from metrics to PURPOSE. Point at the user's health north-star (why the training matters to them: the activity they want to keep doing, the people they want to keep pace with, the life they're training for — pulled from health.md/life.md), not another wall of green. Praise must be earned and scarce: one clear, specific line, not a generic "good job."

## Step 5 — Compose the email
To: {{USER_EMAIL}}
Subject: 🩺 Monthly Health Memo — <month, year>
~250 words. Plain voice. Sections above, omitting any that don't apply this month. Action items get mailto: acknowledgment links.

## Step 6 — Update memory
Write the month's trajectory into health.md > Wearable data > Monthly trajectory.
Add any new active concern that emerged. Add a genuine insight (if any) to insights.md.

Confirm with: "Monthly health memo sent. <N> action items. Pre-bloodwork section: <included/omitted>."
```

---

## Customization notes

- **~250 words is the cap.** The monthly memo earns its length by being rare and high-altitude. If it sprawls into a full panel readout, it becomes the thing you skim and ignore.
- **The pre-bloodwork branch is the highest-leverage part.** Set your two draw months in `health.md`; the memo fires the prep section the month before each. Walking into a draw with wearable-informed questions changes the conversation with your doctor.
- **Genetic-context is optional.** If you have no genome data, the memo simply skips that section. If you do, store *risk priors* (not raw reports) in `health.md` — see [`docs/health-system.md`](../docs/health-system.md).
- **The all-green pivot is the point of earned praise.** A month with nothing to fix shouldn't produce a memo full of green checkmarks — it should remind you *why you're doing this at all.*
- **If you use a different wearable platform** (Whoop / Oura / Apple Health / Garmin), swap the data source. The five-section recipe is generic.
