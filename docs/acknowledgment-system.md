# The Acknowledgment System

How the exocortex closes the loop on offline actions.

---

## The problem this solves

Every personal AI runs into the same wall. You commit to something. The agent flags it. You do it — but you do it *offline*. You call your mom on the way home from work. You stop by the dry cleaner on a lunch break. You hand your kid a permission slip.

There's no digital trace. The agent has no way to know it happened. So tomorrow morning, it flags the same thing again. And the day after. And eventually you stop reading the briefings because they're full of stale items.

This is the death loop of personal AI. We had to solve it.

---

## The solution: mailto: links + coded subjects

Every action item in a briefing email includes a one-tap link:

```html
<a href="mailto:you@example.com?subject=EXO_DONE%3A%3Acall-mom">✅ I did this</a>
```

You tap it. Your mail app opens with the subject pre-filled. You send the email to yourself.

The next briefing runs Step 0:

```
Search Gmail for subject:EXO_DONE in the last 36 hours.
For each match:
  - Extract the slug after EXO_DONE::
  - Find matching commitment in commitments.md (the `Slug` column)
  - Set State to DONE, move the row to `Closed (last 7 days)`, write one journal `closed` line
  - Archive the signal email
```

Loop closed.

---

## Why this works (vs. alternatives we tried)

**Alternative 1: A check-off web app.**
Tried it. Friction is too high. Opening an app to confirm "yes I called my mom" defeats the point. Tap-tap-send is one motion, fits inside the briefing email, requires zero new infrastructure.

**Alternative 2: Voice replies / Siri shortcuts.**
Brittle across platforms. Doesn't work consistently. Email works everywhere.

**Alternative 3: Just ask the user every morning.**
"Did you call your mom yesterday?" Conversational, but slow and exhausting. Doesn't scale past ~3 items.

**Alternative 4: Infer from data.**
"Your phone shows a 12-minute call to mom's number at 5:47pm." This works for *some* actions but breaks for in-person things, paper actions, anything not on a tracked device. And it's invasive — you have to grant the agent call-log access.

The mailto: link is the simplest thing that works. It piggybacks on infrastructure (email) that's universal, opt-in (you choose to tap), and asynchronous (no waiting on the agent).

---

## The slug format

Slug rules:

- Lowercase
- Spaces → hyphens
- Strip non-alphanumeric (except hyphens)
- Max 40 characters
- Derived from the commitment title

Examples:

| Commitment | Slug |
|------------|------|
| Call parents | `call-parents` |
| Reply to lawyer re: case | `reply-to-lawyer-re-case` |
| Pay Q3 estimated taxes | `pay-q3-estimated-taxes` |
| Send Sarah the apartment listing | `send-sarah-the-apartment-listing` |

URL-encode `::` as `%3A%3A` in the mailto href.

Full HREF: `mailto:you@example.com?subject=EXO_DONE%3A%3Acall-parents`

---

## Matching logic in Step 0

The briefing's Step 0 does fuzzy matching to be forgiving:

1. **Exact slug match.** If a `commitments.md` row has that exact value in its `Slug` column, mark it done.
2. **Title fuzzy match.** If no exact slug match, compute slugs from each PENDING commitment's title. Pick the closest by Levenshtein distance, threshold 3.
3. **No match.** If still nothing, surface in the briefing email's "Loose Ends" section: "You acknowledged `call-mom-tonight` but I can't find a matching commitment. Should I add it as a one-off done?"

This handles the case where you typed the slug yourself or it drifted from the original commitment.

---

## Fallback: free-text parsing

If the user replies to a briefing email with text (instead of tapping a link), the agent also tries to parse "done" markers:

- `"done: call-mom"` — explicit
- `"did it"`, `"called"`, `"sent"` — implicit, requires context match to the most recent briefing
- `"✅"` followed by a slug — emoji format

Use this as a fallback. The primary path should be the mailto link.

---

## Cleanup: archiving signals

After processing, signal emails are archived (or trashed) so the inbox stays clean.

```
For each processed EXO_DONE email:
  - Apply Gmail label "exo-archive"
  - Remove from INBOX
  - (Optional) Move to Trash if older than 30 days
```

This matters because over a year, you'll send yourself thousands of these. Keeping them in INBOX would be noise.

---

## Edge cases

**Tapping a link by accident.**
You tap "I did this" but you didn't actually do it. Easy fix: open commitments.md, move the row back to its Open section, and set State to PENDING. The exocortex will catch up on the next briefing (and the journal-diff logs the reopen).

**The same action surfaces multiple times across briefings before you tap.**
Step 0 only processes signals received *since the last briefing*. If you tapped 3 times, only the first is matched; the rest are ignored.

**You reply to the briefing email instead of tapping a link.**
Falls through to free-text parsing. Less reliable, but works.

**You forget to tap and the commitment ages out.**
After 21 days open, the script marks it `CHRONIC`. It drops to one compact line in briefings, and the weekly review asks once whether to keep, accept (stop tracking), or reframe it, with `EXO_DONE::keep-<slug>` / `EXO_DONE::accept-<slug>` links. Nothing is lost: closed rows are archived to `memory/archive/commitments/`, and `python3 tools/memory_maint.py lookback --grep <slug> --archive` finds its whole history.

---

## Customizing the prefix

Default prefix is `EXO_DONE::`. You can change it in:

- `briefings/morning-brief.md` (Step 0)
- All other briefing prompts (Step 0)
- The mailto link generators in each briefing

Pick something unique to your setup. `JARVIS_DONE::`, `BRAIN_DONE::`, `OPS::DONE::` all work. The point is just that it's a subject prefix the agent can search reliably and that you won't accidentally produce in normal email.

---

## When this breaks

The acknowledgment system depends on:

1. **Gmail (or your email provider) being searchable** — true for Gmail, Outlook, Fastmail. Less reliable for some self-hosted setups.
2. **mailto: links opening your mail app** — true on iOS, Android, and most desktops. If the user has stripped mailto handlers, this won't work.
3. **The user being willing to tap one extra time** — this is the only ask. If you can't summon the energy to tap "✅ I did this," the loop won't close. (In practice, this isn't an issue — the tap is faster than ignoring the email.)

---

## Why this is the secret sauce

Most personal AI systems are weakest at the bridge between digital and physical. The acknowledgment loop is what makes the exocortex feel real — because actions you take in the world actually update its state.

Without it, you have a smart inbox.
With it, you have an operator.
