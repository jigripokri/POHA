# Commitment → Calendar

**Schedule:** `0 7 * * *` (7am daily)
**Output:** Calendar events created. Optional summary email if anything ambiguous.

Takes everything flagged `CALENDAR NEEDED` in commitments.md and triages it three ways: real events, GSD blocks, or urgent action slots.

---

## Prompt

```
You are running the commitment-to-calendar sweep for {{USER_NAME}}. Don't email unless there's something to escalate.

## Step 1 — Memory load

Follow the **Open** steps in [`_memory-contract.md`](./_memory-contract.md): read `memory/INDEX.md` first, then only what this briefing's row in `INDEX > Read plan` marks `full`; everything else by section or grep. For this briefing: memory/INDEX.md, then only the open sections — `python3 tools/memory_maint.py section memory/commitments.md "Open — I Said I Would"` (and "Open — They Said They Would").
Filter: State = `CALENDAR NEEDED` (or `PENDING` with a Due date). **Skip CHRONIC rows entirely** — they never get routed or auto-scheduled; the weekly decides them. No candidates is a correct outcome: write the run note and stop.

## Step 2 — Read Calendar

List events in the next 14 days. Use this to detect conflicts and find slots.

## Step 3 — Triage each commitment

For each `CALENDAR NEEDED` item, apply this decision tree:

**A. Has explicit date AND time?**
- Create a calendar event for that date/time.
- Default duration: 30 min unless content suggests longer (dinner = 90 min, day trip = block the day).
- Event title: <short description>. Add notes with full context.
- Update commitment status to `SCHEDULED`.

**B. Has explicit date, no time?**
- Find a slot on that date (avoid conflicts, prefer mid-morning or after lunch).
- Apply rules from CLAUDE.md > Calendar Event Rules.
- Update status to `SCHEDULED`.

**C. Has no date but is non-urgent?**
- Park it in the next Friday GSD Hour block (see gsd-friday.md).
- Update status to `PARKED_GSD`.

**D. Is urgent (e.g., flagged OVERDUE, or content suggests urgency)?**
- Block the 6–7am slot tomorrow as "Critical action: <title>".
- Update status to `URGENT_SCHEDULED`.

**E. Ambiguous (no clear date, unclear urgency)?**
- Flag for an email. Don't auto-schedule.

## Step 4 — Conflict detection

If creating any event would conflict with:
- Existing events
- "Never schedule" blocks defined in CLAUDE.md (e.g. family dinner, GSD Hour, sleep)

...don't create it. Add to the flagged-for-email list.

## Step 5 — Compose escalation email (only if needed)

If there are flagged ambiguous or conflicting items, send a short email:

Subject: 📅 Calendar triage needs your call — <N> items

Body: numbered list of items, with the question (e.g., "Coffee with X: no time specified. Pick: Sat 10am, Sun 2pm, Tue 5pm?")

Include reply links: `mailto:` with `EXO_DECIDE::<slug>::<option>` subjects.

## Step 6 — Update memory

Edit each row in place (State, Touched = today, Note = `cal <date time>` for created events) and write one journal `calendar` line per event created (≤4 per run).

Then the **Close** steps in [`_memory-contract.md`](./_memory-contract.md): save the briefing, update line-3 headers, `memory_maint.py run-note`, `memory_maint.py all --job c2c`.

Confirm with: "<N> events created, <M> parked to GSD, <K> flagged for your call."
```

---

## Customization notes

- **The 6–7am "critical action" slot is opinionated.** If you're not a morning person, change this to whatever your "free" time is — lunch, evening, etc.
- **GSD parking only works if you have a recurring GSD block on your calendar.** Set that up first.
- **Conflict detection is more important than you think.** Without it, the exocortex will happily schedule over your kid's bedtime.
