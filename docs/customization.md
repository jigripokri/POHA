# Customization

The whole point of forking this repo is to make it yours. Here's the spectrum of customization from light to deep.

---

## Light: tune what's there

These changes don't add anything new — they make the default setup fit your life.

### 1. Persona
Edit the `Persona` section of `CLAUDE.md`. The default is "direct, warm, slightly cheeky." Variations:

- **Softer**: "warm, encouraging, patient. Asks rather than tells. Reframes setbacks as data."
- **Sharper**: "blunt, unsentimental, allergic to excuses. Names patterns you'd rather not see."
- **More technical**: "engineer-coded. Roots arguments in first principles. Skeptical of consensus."

### 2. Tier system
The default tiers (Family / Meaningful work / Health) are placeholders. Replace with what actually matters to you:

- Founder: Cofounders / Investors / Side project
- Parent of young kids: Family / School community / Self
- Career-builder: Mentors / Direct reports / Sponsors

The tier system controls filtering everywhere — high-tier people surface first in briefings.

### 3. Scheduled task timing
The defaults (5am, 9pm, etc.) match a typical morning person. If you're a night owl, shift everything 2–3 hours later. The morning brief should arrive 60–90 min before your alarm.

### 4. Tracked projects
`CLAUDE.md` has a `#1 Tracked Project` slot. Use it for the one long-running thing you most fear losing track of. Examples:

- A fundraise
- An immigration case
- A medical situation for a family member
- A house renovation
- A book you're writing

Update it when the project changes.

---

## Medium: edit the briefings

Each briefing in `briefings/` is a standalone prompt. Edit them.

### Common edits

**Remove a section you don't care about.**
e.g., if you don't track health data, delete the Google Health step from `morning-brief.md` (and skip the weekly/monthly health surfaces).

**Add a section for your situation.**
e.g., a founder might add to `morning-brief.md`:

```
## Step 9 — Today's narrative

In one sentence: what's the story we'd tell about today if today went well? Surface this at the top of the email under "🎯 Today's three."
```

**Change the email format.**
The default is markdown-ish. You can switch to plaintext, formal HTML, or whatever fits your reading habits.

**Adjust the output length.**
If briefings feel too long, add to the prompt:

```
Hard cap: 600 words. If exceeded, ruthlessly cut. The cap is the cap.
```

If they feel too thin, raise the cap and unlock more sub-sections.

---

## Medium: add a per-person memory file

For someone in your life with ongoing complexity — a kid, an aging parent, a co-founder, a high-touch report — create `memory/<name>.md`.

Template:

```markdown
# <Name>

## Profile
Age, role/relationship, location, current life stage.

## What's current
What's happening with them right now (the things you'd update monthly).

## Recurring themes
Patterns you want to remember (the things that don't change month to month).

## History
Important past events that explain the present.

## Open threads
| Status | What | Notes |

## Notes
Free-form. Anything else.
```

Tell `CLAUDE.md` about this file:

```markdown
## Per-Person Memory Files
- `memory/<name>.md` — Read when this person is the subject of a conversation or surfaced in a briefing.
```

This is one of the highest-leverage extensions. It lets the exocortex maintain genuine context on the 3–5 people who need it.

---

## Medium: add a new briefing

Want a daily reflection on your business? A weekly review of your fitness data? A custom monthly review?

Add a new file in `briefings/`. Use the existing ones as templates. Follow the recipe:

1. **Step 0**: Acknowledgment scan
2. **Step 0.5**: Health check
3. **Step 1**: Memory load
4. **Steps 2..N**: Do the work
5. **Step N+1**: Update memory + send

Then ask Claude:

> *"Set up a scheduled task at <time> on <cadence> that runs the prompt in briefings/<new-briefing>.md."*

Common additions:

- **Daily journaling prompt** — emails you 3 questions to answer
- **Weekly investing review** — reads your portfolio + relevant news
- **Monthly relationship check-in** — deeper than the weekly review
- **Quarterly OKR check** — pulls quarterly goals from life.md, asks "honestly: are these still real?"
- **Daily "what moved the needle" reflection** — founder-mode

---

## Deep: add a new skill

Skills are on-demand commands. They live in `skills/<name>/SKILL.md`. The format follows Claude's Skills convention.

Template:

```markdown
---
name: <skill-name>
description: <one-line description for skill matching>
---

# <Skill Name>

<Prompt the skill executes when invoked.>
```

Ideas:

- `/standup` — generate today's standup update for your team
- `/decide` — runs a structured decision framework on whatever question you bring
- `/playdate` — finds 2–3 plausible play dates this weekend from your network
- `/onepager` — turns a memory file or a conversation into a polished one-pager doc
- `/airbnb-it` — quick analysis: should this trip be Airbnb or hotel?
- `/journal` — interactive journaling, writes to a private journal file

---

## Deep: add a new data source

Connect a new MCP. Then:

1. **Add to CLAUDE.md > Data Source Priorities.**
2. **Add health-check entry to Step 0.5 of relevant briefings.**
3. **Decide which briefings read it.** Usually morning brief, possibly a domain-specific briefing.
4. **Map fields to memory files.** New financial data → finances.md; new wearable data → health.md.

See `docs/data-sources.md` for full guidance.

---

## Deep: change the architecture

If you want to depart from the three-layer model, the choices are:

**Replace markdown memory with a database.**
Trade-offs: gain queryability, lose human-editability. Only do this if your memory is bigger than ~500KB across files (it shouldn't be).

**Replace the acknowledgment loop with something else.**
Voice replies, a check-off app, automatic inference from data. Each has trade-offs (see `docs/acknowledgment-system.md`). The mailto: approach is the local optimum but not the only option.

**Run briefings on the server instead of the client.**
Trade-offs: gain consistency (no laptop-asleep problem), lose privacy (memory leaves your machine). Usually not worth it.

---

## What NOT to customize (until you've used it for a month)

These are tempting but premature optimizations:

- **Don't tighten the prompts on day one.** Let the exocortex over-share initially. You need to see what it surfaces before you know what to filter.
- **Don't connect 6 data sources right away.** Start with 2. Add one per week.
- **Don't write a new briefing until you've used the default 7 for a few weeks.** You don't know what's missing until you've felt it.

---

## When you've extended in cool ways

Open a PR. Specifically interesting:

- New per-role configurations (founder edition, student edition, retiree edition)
- New connectors (Apple Notes, Things, Roam, Obsidian, etc.)
- New briefing types
- New skills

The base repo stays minimal. The community library of extensions is where the depth lives.
