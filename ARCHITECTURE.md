# Architecture

Exocortex is three layers stacked on top of Claude. Each layer is independently useful; together they're the system.

```
                    ┌─────────────────────────────┐
                    │   YOU (the human)           │
                    │   reads briefing emails     │
                    │   taps "I did this" links   │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   Claude (the reasoning)    │
                    └──┬──────────┬───────────┬───┘
                       │          │           │
            ┌──────────▼──┐  ┌────▼────┐ ┌────▼────┐
            │  Layer 1    │  │ Layer 2 │ │ Layer 3 │
            │  Briefings  │  │ Memory  │ │ Skills  │
            └──────────┬──┘  └────┬────┘ └────┬────┘
                       │          │           │
                       └──────────┼───────────┘
                                  │
                    ┌─────────────▼─────────────────┐
                    │  MCP Connectors               │
                    │  WhatsApp · Gmail · Calendar  │
                    │  Tasks · SMS · Health · etc.  │
                    └───────────────────────────────┘
```

---

## Layer 1: The Briefing Engine

The heartbeat. Seven scheduled tasks that run automatically and produce structured output (usually emails to yourself).

Every briefing follows the same five-step recipe:

**Step 0 — Acknowledgment scan.** Search Gmail for `subject:EXO_DONE`. Extract slugs, match to `commitments.md`, update status to ✅, archive the signal emails. This is how offline actions close the loop.

**Step 0.5 — Data source health check.** Ping every MCP in parallel, record UP/DOWN. If anything is unreachable, surface a `⚠️ DEGRADED` banner in the email. Never block the briefing — a degraded briefing is better than no briefing. Two special cases: **WhatsApp** needs a *liveness assertion* (connected + traffic in the last 24h), because an empty scan from a dead bridge looks exactly like a quiet day; and **health** is non-blocking and noise-suppressed (silent on a single down-day, `DEGRADED` only after several). See [`docs/data-sources.md`](./docs/data-sources.md#health-check-protocol-step-05).

**Step 1 — Memory load.** Read the seven memory files. This is the operator's context for everything that follows.

**Step 2..N — Scan inputs.** WhatsApp groups, DMs, Gmail, Calendar, Tasks, SMS, Google Health, Monarch — whatever this briefing needs. Always parallelize. Apply tier weights so high-signal threads surface first.

**Step N+1 — Emit + Update.** Compose the email with action items + acknowledgment links. Update memory files with anything new (commitments made, plans confirmed, insights surfaced). Send.

The seven briefings in this repo:

| Briefing | When | What it does |
|----------|------|--------------|
| `morning-brief.md` | 5am daily | The big one — full sweep |
| `evening-reflection.md` | 9pm daily | Lighter pass, catches what morning missed |
| `weekly-review.md` | Sun 9am | Memory pruning + priority refresh |
| `commitment-to-calendar.md` | 7am daily | Triage commitments → calendar events |
| `gsd-friday.md` | Fri noon | Punch list for Friday focus block |
| `weekend-fun-finder.md` | Fri noon | Local event search, scored for your family |
| `monthly-finance.md` | 28th | Spending, net worth, subscriptions, credit cards |

Each briefing is a standalone prompt in [`briefings/`](./briefings/). You can run them manually any time by invoking them in Claude.

### Scheduling

Briefings are wired up using Claude's scheduled tasks. Once you've validated a briefing prompt manually, ask Claude:

> *"Set up a scheduled task at 5am daily that runs the prompt in briefings/morning-brief.md."*

Claude creates the cron entry. You can list, update, and delete scheduled tasks the same way.

---

## Layer 2: The Memory System

Seven files. Plain markdown. They are the exocortex.

### Core four (general life)

| File | Purpose |
|------|---------|
| `people.md` | Relationship context. Who matters, open threads, last contact, birthdays, kids' names, things that came up that you should remember next time. |
| `commitments.md` | Promises. Two sections: "I Said I Would" and "They Said They Would." Each item has a status (PENDING / CALENDAR NEEDED / DONE) and a date. |
| `life.md` | Goals, priorities, quarterly view. The horizon document. |
| `insights.md` | Non-obvious patterns. Things worth re-reading in a year. Wildcards. The exocortex's strategic lens. |

### Domain three (specific contexts)

| File | Purpose |
|------|---------|
| `finances.md` | Net worth snapshot, properties, FIRE progress, open financial decisions. Read only when a financial question arises. |
| `health.md` | Bloodwork baselines, fitness routine, active concerns, doctor info. Read only when a health question arises. |
| `<person>.md` *(optional)* | Per-person context for someone who needs ongoing tracking — a kid, an aging parent, a high-touch direct report. One file per person who needs it. |

### Private (gated)

| File | Purpose |
|------|---------|
| `memory/private/carry-on.md` | Sensitive context. **Strictly gated.** Never read automatically. Never referenced in any outbound message. Never mentioned unprompted. Only loaded when you explicitly invoke it. |

### Operating rules

- **Read at start, update at end.** Every briefing reads the four core files at Step 1 and updates them at Step N+1.
- **3-week rule.** If an item in memory hasn't been referenced or relevant in 3 weeks, archive or remove it during weekly review. Memory stays tight.
- **Save if it will matter in 1+ weeks.** Major decisions, recurring relationships, active deadlines, non-obvious patterns. **Don't save** completed one-off tasks, social chatter, anything re-derivable from re-scanning inputs.
- **Memory is not a journal.** It's working state for the operator. Keep it tight.

Full breakdown in [`docs/memory-system.md`](./docs/memory-system.md).

---

## Layer 3: Skills

On-demand commands. Invoke them in Claude any time.

| Skill | What it does |
|-------|--------------|
| `/draft` | Writes outbound messages in your voice. Studies the last 10–20 messages in any thread before drafting. Never sends without explicit "send it" approval. |
| `/reply` | Three reply options + a recommendation for any message thread. |
| `/wildcard` | One contrarian, non-obvious insight on whatever's on your mind. |
| `/gsd` | Prioritized punch list from tasks + commitments, right now. |
| `/roast` | Group-chat roast on demand. Tune it to your circle's tone. |

Each lives in [`skills/<name>/SKILL.md`](./skills/) and is a standalone prompt. Add your own — the founder version probably wants `/standup` (today's update for the team), the parent version probably wants `/playdate` (find a play date in your network this weekend).

---

## Data Sources

The exocortex is only as good as what it can see. Recommended connectors:

| Source | Method | Why it matters |
|--------|--------|----------------|
| **WhatsApp** | Native MCP (whatsmeow/Go bridge, native name resolution) | Most personal conversation lives here for non-US users; commitments hide in here |
| **Gmail** | Native MCP | Acknowledgment loop runs through this |
| **Google Calendar** | Native MCP | Where commitments turn into events |
| **Google Tasks** | Chrome scraping (no MCP yet) | Source of truth for "things I need to do" |
| **Android Messages** | Chrome → messages.google.com | For SMS-only contacts (US carriers) |
| **Google Health** | Plugin with OAuth (read-only) | Reconciled wearable stream — sleep, RHR, HRV, weight — feeds the health surfaces + health.md |
| **Monarch Money** | Local MCP server (read-only) | Source for the monthly financial sweep |

Full setup in [`docs/data-sources.md`](./docs/data-sources.md). Known gotchas (WhatsApp bridge durability + liveness, the now-resolved LID migration) in [`docs/whatsapp-gotchas.md`](./docs/whatsapp-gotchas.md).

---

## The Acknowledgment Loop (the secret sauce)

Without this, briefings become noise. With it, the exocortex actually closes loops.

The mechanism:

1. **Outbound:** Every action item in a briefing email gets a tappable link: `mailto:you@example.com?subject=EXO_DONE%3A%3A{{slug}}`
2. **You tap.** Mail app opens with a pre-filled subject. You send.
3. **Inbound:** Next briefing's Step 0 searches Gmail for `subject:EXO_DONE`, extracts slugs, matches to `commitments.md`, marks ✅.
4. **Cleanup:** Signal emails are archived/trashed.

Slug format: lowercase, hyphens, max 40 chars. `"Call parents"` → `call-parents`. URL-encode `::` as `%3A%3A`.

Why this matters: this is the only mechanism that catches phone calls, in-person conversations, and other actions that leave no digital trace. Without it, "call mom" gets flagged every morning forever, even after you called her.

Full details in [`docs/acknowledgment-system.md`](./docs/acknowledgment-system.md).

---

## Voice & drafting authorization

The exocortex has explicit authorization to draft outbound messages in your voice. Drafts are never sent without your "send it" approval.

The drafting rules (set in `CLAUDE.md`):

- Study the last 10–20 messages in any thread before drafting — mirror cadence, vocabulary, sentence length.
- Match the tone of the channel (group chat ≠ work email).
- Reference something specific from the conversation — callbacks, shared jokes, things they mentioned.
- Always wait for explicit approval before sending. "Send it" or "send A/B/C" = green light.

---

## Why not a SaaS?

Three reasons this is a fork-and-own repo, not a hosted product:

1. **Your memory is too sensitive to hand to anyone.** The whole point is that the system knows enough about your life to be useful. That trust radius should end at you.
2. **The configuration is the product.** A SaaS version would have to abstract over your specific tier system, relationships, and voice — and that's where 80% of the value sits.
3. **Lock-in is the enemy.** Markdown files in your repo are portable forever. A vendor database isn't.

If someone builds a hosted version, that's their call. This repo will always be the canonical, you-own-the-state version.
