# POHA

**Personal Overnight Helper Agent. Runs while you sleep. Serves up a morning brief before your alarm. Forks in 30 minutes. Runs on your existing Claude subscription.**

Built an AI that runs overnight and serves up a morning brief. Called it POHA, because of course.

The pun completes itself: POHA is the breakfast you wake up to. This agent literally runs overnight and delivers a morning brief before your alarm. The dish IS the deliverable.

---

## What POHA is (and isn't)

Most "AI assistants" are reactive. You open them, you type, they answer, you close them, nothing persists. That's a tool, not a brain extension.

POHA has three properties:

1. **It observes.** Reads your inbound — WhatsApp, Gmail, Calendar, Tasks, SMS — without you having to ask.
2. **It remembers.** Persistent state across sessions, in plain markdown you can edit by hand.
3. **It acts on a schedule.** Runs while you sleep. The morning briefing is on your phone before your alarm.

This repo wires all three.

---

## What you get on day one

Nine scheduled tasks already wired up:

- **5am daily — Morning briefing.** Scans your WhatsApp groups + DMs, Gmail, Calendar, and tasks. Flags commitments, unanswered threads, and what's on your plate today. Emails you the result with one-tap acknowledgment links for every action item.
- **9pm daily — Evening reflection.** Catches plans confirmed after the morning pass, updates memory.
- **Sunday 9am — Weekly review.** Prunes stale memory (3-week rule), refreshes priorities, reviews relationship health.
- **7am daily — Commitment → Calendar.** Turns every "let's grab coffee Saturday" into a real calendar event.
- **Friday noon — GSD agenda.** Builds a punch list from your tasks + open commitments for a Friday focus block.
- **Friday noon — Weekend Fun Finder.** Searches local events, scored against your household's preferences.
- **28th monthly — Financial sweep.** Spending autopsy, net worth update, subscription audit, credit card optimization.
- **28th monthly — Health memo.** A ~250-word trajectory read on vitals, training load, and sleep from your wearable (via Google Health) — silent on the daily noise, surfacing only what's trending.
- **Twice yearly — Bloodwork reminder.** The month before each draw, preps a doctor ask-list mapping your wearable trends to questions worth asking.

Five on-demand skills:

- `/draft` — Writes outbound messages in your voice. Studies the last 10–20 messages in any thread before drafting.
- `/reply` — Three reply options + a recommendation for any message thread.
- `/wildcard` — One contrarian, non-obvious insight on whatever's on your mind.
- `/gsd` — Prioritized punch list, right now.
- `/roast` — Group-chat roast on demand. Tune it to your circle's tone.

---

## The three architectural unlocks

Most personal-AI projects fail in predictable ways. Here's what we did differently.

**1. Persistent memory in plain markdown.** Seven files. Claude reads them at the start of every task, updates them at the end. No vector DB. No RAG. No fine-tuning. Just files. The reason this works: markdown is human-editable, version-controllable, and grep-able. You can correct POHA's memory by opening a file in any editor. You own the state. (See [`docs/memory-system.md`](./docs/memory-system.md).)

**2. The acknowledgment loop.** This is the hardest problem in personal AI: how do you close the loop on actions that happen offline? You called your mom. There's no API event. The agent has no way to know.

Solution: every briefing email includes one-tap `mailto:` links next to action items. Tapping one fires a self-email with a coded subject — `EXO_DONE::call-mom` — that the next briefing parses. Match the slug, mark the commitment done, archive the signal. (See [`docs/acknowledgment-system.md`](./docs/acknowledgment-system.md).)

**3. Tier-weighted attention.** Not all messages are equal. The morning sweep applies five tiers (Family → Extended family → Close friends → Network → Other), so a "hey when are you free?" from your partner surfaces before a meme from a group chat. The tier system is in `CLAUDE.md` — change it to match your life. (See [`docs/customization.md`](./docs/customization.md).)

---

## Architecture

Three layers. Full breakdown in [`ARCHITECTURE.md`](./ARCHITECTURE.md).

```
┌──────────────────────────────────────────────────────────┐
│ Layer 1 — The Briefing Engine (scheduled tasks)           │
│   morning · evening · weekly · daily commitment sweep ·   │
│   GSD agenda · weekend finder · monthly finance ·         │
│   monthly health memo · bloodwork reminder                │
├──────────────────────────────────────────────────────────┤
│ Layer 2 — The Memory System (seven markdown files)        │
│   people · commitments · life · insights ·                │
│   finances · health · carry-on (private, gated)           │
├──────────────────────────────────────────────────────────┤
│ Layer 3 — Skills (on-demand commands)                     │
│   /draft · /reply · /wildcard · /gsd · /roast             │
└──────────────────────────────────────────────────────────┘
         ▲
         │ reads/writes via MCP connectors
         ▼
┌──────────────────────────────────────────────────────────┐
│ WhatsApp (whatsmeow/Go bridge, native name resolution) ·  │
│ Gmail · Google Calendar · Google Tasks ·                  │
│ Android Messages · Google Health · Monarch Money          │
└──────────────────────────────────────────────────────────┘
```

---

## Quickstart

Full walkthrough in [`SETUP.md`](./SETUP.md). The 30-second version:

1. Install [Claude Desktop](https://claude.ai/download) with Cowork mode enabled.
2. Clone this repo somewhere stable on your machine.
3. Mount the folder in Cowork.
4. Open [`CLAUDE.md`](./CLAUDE.md) and fill in the placeholders (`{{USER_NAME}}`, `{{PARTNER_NAME}}`, your tier system, etc.).
5. Connect the MCPs you want — WhatsApp, Gmail, Calendar are the high-leverage trio.
6. Tell Claude: *"Read CLAUDE.md and onboard me. Walk me through filling in the memory files."*
7. Once memory is bootstrapped, tell Claude: *"Set up the seven scheduled tasks per BACKLOG.md."*

The first morning brief lands at 5am the next day. Hot and ready, like the dish.

---

## Customize

Three knobs to turn:

**Persona.** Edit the `Persona` section of `CLAUDE.md`. The default is "direct, warm, slightly cheeky chief of staff who tells you what you need to hear, not what you want to hear." If you want softer or more sarcastic, change it there. Every output inherits.

**Tier system.** The default tiers are placeholder categories (Family / Meaningful work / Health). Yours might be Cofounders / Investors / Side project. Whatever they are, write them down — POHA filters everything through this lens.

**Scheduled tasks.** Each briefing in [`briefings/`](./briefings) is a standalone prompt. Edit them, remove the ones you don't want, add new ones for your situation. The founder version probably wants a daily "what moved the needle?" reflection. The new-parent version probably wants a school-pickup buffer alert.

See [`docs/customization.md`](./docs/customization.md).

---

## What it costs

- **Claude Pro or Max subscription**: already what you're paying. Max recommended if you're running all seven scheduled tasks against a busy life.
- **MCP connectors**: free for personal accounts (Gmail, Calendar, WhatsApp, Google Health). Monarch Money is $15/mo if you want financial sweeps.
- **Your time**: ~3 hours upfront to bootstrap memory honestly. ~5 min/week to review what POHA surfaces. The 3 hours pay back inside a month.

---

## Who this is for

You will get value out of this if you:

- Run a complicated life (family + work + side projects + community + investing) and lose threads regularly.
- Already use Claude a lot and feel the pain of starting from scratch every conversation.
- Are willing to write down what actually matters to you in markdown.

You will not get value if you:

- Want a chatbot you talk to. POHA runs in the background; you barely interact with it.
- Are uncomfortable letting an LLM read your messages and email. It does. It has to.
- Want zero configuration. The configuration *is* the product — your context is what makes it work.

---

## Privacy & safety

- All memory lives on your machine. Nothing leaves your laptop except Claude API calls and the briefing emails you send to yourself.
- The `memory/private/carry-on.md` file is *strictly gated* — never read automatically, never referenced in any output, only loaded when you explicitly invoke it. Use it for anything sensitive.
- `.gitignore` excludes `memory/` from version control by default. Your second brain stays out of GitHub.
- Read [`docs/privacy.md`](./docs/privacy.md) before connecting anything financial or medical.

---

## Repo map

```
poha/
├── README.md                  ← you are here
├── ARCHITECTURE.md            ← the three-layer system, in depth
├── SETUP.md                   ← step-by-step onboarding
├── BACKLOG.md                 ← what to build next (yours to fork)
├── CLAUDE.md                  ← the persona + ruleset (fill in placeholders)
├── memory/                    ← your second brain (gitignored)
│   ├── people.md.template
│   ├── commitments.md.template
│   ├── life.md.template
│   ├── insights.md.template
│   ├── finances.md.template
│   ├── health.md.template
│   └── private/carry-on.md.template
├── briefings/                 ← the seven scheduled task prompts
├── skills/                    ← /draft, /reply, /wildcard, /gsd, /roast
├── docs/                      ← deep dives on tricky bits
└── examples/                  ← a sanitized example morning briefing
```

---

## Contributing

If this is useful, star the repo — it helps others find it. If you've extended it in interesting ways (new briefing types, new connectors, new skills), open a PR. I'd especially love to see versions tuned for founders, students, parents of young kids, and retirees.

## License

MIT. Take it, fork it, sell it, whatever. Just don't claim you invented the acknowledgment loop without crediting it — that one took a while to figure out.
