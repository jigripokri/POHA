# BACKLOG

What's shipped, what's next, what's blocked. Edit this for your fork.

> **How to use this file:** This is the source of truth for what the exocortex is and what it should become. Update it when features ship or priorities change. Read it whenever assessing what to build next.

---

## ✅ Shipped (in this template)

### Layer 1 — Briefing Engine
- ✅ Morning brief (5am daily)
- ✅ Evening reflection (9pm daily)
- ✅ Weekly review (Sun 9am)
- ✅ Commitment → Calendar (7am daily)
- ✅ GSD Friday agenda (Fri noon)
- ✅ Weekend Fun Finder (Fri noon)
- ✅ Monthly Financial Sweep (28th)
- ✅ Monthly Health Memo (28th)
- ✅ Bloodwork reminder (twice-yearly, the month before each draw)

### Layer 2 — Memory System
- ✅ Seven memory file templates
- ✅ 3-week rule baked into weekly review
- ✅ Carry-on gating

### Layer 3 — Skills
- ✅ /draft
- ✅ /reply
- ✅ /wildcard
- ✅ /gsd
- ✅ /roast

### Infrastructure
- ✅ Acknowledgment loop (mailto: + Step 0 scan)
- ✅ Step 0.5 health check (+ WhatsApp bridge-liveness assertion)
- ✅ MCP connections documented for Gmail, Calendar, WhatsApp, Tasks, SMS, Google Health, Monarch

### Migrations (completed)
- ✅ **WhatsApp: Baileys (TS) → whatsmeow (Go) bridge** — native LID/name resolution, no more dual-JID juggling; persistent startup-triggered service + bridge-liveness assertion. *(2026-06)*
- ✅ **Health: Fitbit Web API → Google Health API** — reconciled multi-source stream, briefings call the health MCP directly (sync script retired), four cadence-tuned health surfaces. *(2026-06)*

---

## 🎯 Build Next (your starter list — edit freely)

These are the highest-leverage extensions. Pick what fits your life.

- [ ] **Per-person memory file** for someone you need ongoing detailed context on (kid, parent, co-founder, high-touch report)
- [ ] **A daily reflection prompt** tuned to your work (founder: "what moved the needle?"; student: "what did you actually learn?")
- [ ] **A custom skill** for a recurring thing you do (e.g., `/standup`, `/decide`, `/journal`)

---

## 💡 High Impact (worth doing in month 2–3)

- [ ] **Per-domain skills**: e.g., `/onepager` (turn a conversation into a polished doc), `/decide` (run a structured decision framework)
- [ ] **Custom briefing**: a weekly investing review, a monthly health deep-dive, a daily standup-prep
- [ ] **A second-opinion skill**: `/devils-advocate` for important decisions
- [ ] **Travel mode**: a different briefing recipe when you're on the road
- [ ] **Family briefing**: a Sunday-night recap email to your partner with the week's family logistics
- [ ] **One-time longitudinal health backfill**: pull the full multi-year history from Google Health once to seed baselines/trajectories, so trend math isn't starting from scratch
- [ ] **Auto-drafted pre-bloodwork ask-list**: turn the monthly memo's pre-draw prep section into a ready-to-send draft for your doctor (wearable trends → concrete questions)

---

## 🔮 Defer (cool ideas; not urgent)

- [ ] **Voice-mode briefings**: have the morning brief read aloud while you make coffee
- [ ] **Briefing widgets**: a phone widget that displays today's three from the morning brief
- [ ] **Cross-device memory sync**: keep memory in sync across multiple machines (probably via a private git repo)
- [ ] **Receipt OCR**: auto-extract expenses from photo receipts into a finance log

---

## 🚧 Blocked

Things that need an upstream change before they're possible.

- [ ] **Apple Reminders connector** — no good MCP yet
- [ ] **WhatsApp call log access** — API doesn't expose this; use self-report or Chrome scraping
- [ ] **Phone-based notification triggers** — Cowork doesn't currently support push notifications

---

## How to prioritize

When deciding what to build next:

1. **Does it close a loop that's currently leaking?** (e.g., I keep forgetting to do X → build the briefing/skill that catches X)
2. **Will I use it weekly?** If not, defer.
3. **Does it depend on something not yet stable?** If yes, blocked.
4. **Can I sketch it in < 30 min?** If yes, just try it.

If you're stuck on what to build, ask the exocortex: *"Read BACKLOG.md and the past 4 weeks of my morning briefings. What's the highest-leverage thing to add next?"*
