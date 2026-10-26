# GSD Friday Agenda

**Schedule:** `0 12 * * 5` (Friday noon)
**Output:** Populates the Friday 1–3pm "GSD Hour" calendar event with a punch list. Optional email summary.

The Friday afternoon focus block. Get Shit Done.

---

## Prompt

```
You are building the Friday GSD agenda for {{USER_NAME}}.

## Step 1 — Memory load

Follow the **Open** steps in [`_memory-contract.md`](./_memory-contract.md): read `memory/INDEX.md` first, then only what this briefing's row in `INDEX > Read plan` marks `full`; everything else by section or grep. For this briefing: memory/INDEX.md and the open sections of memory/commitments.md (`memory_maint.py section`). CHRONIC rows go on the list once, in their own "Chronic — decide, don't do" group, without re-reasoning.

## Step 2 — Source the to-do pool

Gather candidates from:

**A. Google Tasks (primary source)**
Navigate to tasks.google.com via Chrome. Read open tasks from:
- The primary personal list (named in CLAUDE.md)
- The work list (if applicable)
- Any other lists flagged "active" in CLAUDE.md

**B. Open commitments**
From commitments.md, status = `PENDING` or `PARKED_GSD`.

**C. Aging items**
From "They Said They Would" — anything WAITING > 7 days that needs a nudge.

## Step 3 — Prioritize

Rank candidates by:
1. Overdue items first
2. Items blocking other people second
3. Tier 1 priorities third
4. Quick wins (< 10 min) fourth — these go at the end of the block as a sweep

Aim for 5–8 items total. More than that won't fit in 2 hours.

## Step 4 — Build the agenda

Format:

```
🎯 GSD Hour — Friday <date>, 1–3pm

Order:
1. [HARD] <title> — <estimated time> — <one-line context>
2. [MEDIUM] <title> — <time> — <context>
3. [QUICK] <title> — <time>
...

End-of-block sweep (last 15 min):
- <quick win 1>
- <quick win 2>
- <quick win 3>
```

## Step 5 — Update the calendar event

Find the recurring "GSD Hour" event on the Friday calendar.
Replace its description with the agenda above.
(If no recurring event exists, create one and flag this in the email.)

## Step 6 — Optional summary email

Subject: 🎯 GSD Hour at 1pm — your agenda

Body: the agenda + a `mailto:` link for each item.

## Step 7 — Update memory

For each item picked up from commitments.md, set State `IN PROGRESS` (edit in place). One journal `sent` line: list size, overflow count.

Then the **Close** steps in [`_memory-contract.md`](./_memory-contract.md): save the briefing, update line-3 headers, `memory_maint.py run-note`, `memory_maint.py all --job gsd`.
```

---

## Customization notes

- **The Friday 1–3pm slot is opinionated.** Some people do better with a Monday morning GSD block. Move it.
- **The "end-of-block sweep" matters.** Don't skip it. Tiny wins compound and the dopamine carries you into the weekend.
- **If your Google Tasks are a mess, this won't help.** Spend 30 min cleaning them up first.
