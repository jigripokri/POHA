# Data Sources

The exocortex is only as good as what it can see. Here's what to connect, why, and how.

---

## Tiers of connection

Start minimal. Add as you find friction. Don't connect everything on day one.

### Tier 1 — Minimum viable

You need at least these two to have a working system.

#### Gmail (or your email provider)
**Why**: The acknowledgment loop runs through email. Without Gmail (or equivalent), the closing-the-loop mechanism doesn't work.

**How to connect**: Cowork → Connectors → Add Gmail. Authorize.

**What the exocortex needs**: Read + search + draft + label. Compose + send.

**Substitution**: If you don't use Gmail, the same recipe works with any email provider that supports IMAP/SMTP. You'll need to swap the MCP. Open issue if you want help.

#### Google Calendar
**Why**: Where commitments turn into events. Without it, "I'll catch up with X Sunday" stays as a vague intention.

**How to connect**: Cowork → Connectors → Add Google Calendar.

**What the exocortex needs**: Read events, create events, update events.

**Substitution**: Outlook Calendar works. Apple Calendar does not have a great MCP yet.

---

### Tier 2 — High-leverage

Add these once Tier 1 is working.

#### WhatsApp
**Why**: For non-US users, most personal life lives here. Commitments hide in here. Family group chats. Plans get made.

**Recommended bridge**: a native-resolution [whatsmeow](https://github.com/tulir/whatsmeow)-based (Go) MCP bridge. The store resolves contact and group-sender names natively from WhatsApp's own metadata — so names and LIDs come back resolved and you don't hand-maintain phone↔LID mappings.

**How to connect**: Add WhatsApp via your client's connector/MCP config. Scan the QR with your phone. **Wait for full history sync** — 10–30 minutes depending on history size. Don't run briefings until sync completes. **Install the bridge as a persistent background service** (a startup-triggered Scheduled Task / `launchd` / `systemd` unit set to run unattended) so it survives reboots and is alive before your overnight briefings.

**What the exocortex needs**: `list_messages`, `search_messages`, `search_contacts`, `send_message`.

**Known issues**: See [`whatsapp-gotchas.md`](./whatsapp-gotchas.md) — bridge durability, the bridge-liveness assertion (don't trust an empty scan), and the now-resolved LID migration.

#### Google Tasks
**Why**: Source of truth for "things I need to do today." If you keep tasks anywhere (Apple Reminders, Todoist, Notion), the exocortex can integrate via Chrome.

**How to connect**: No native MCP yet. The exocortex accesses Tasks via Chrome (Claude in Chrome MCP) → `tasks.google.com`. Make sure Claude in Chrome is installed and your Google account is signed in.

**Substitution**: Same approach works for any web-accessible task tool — Todoist, Asana, Notion. Adjust the navigation step in the briefings.

---

### Tier 3 — Domain-specific

Add these only if relevant.

#### Android Messages (SMS)
**Why**: For SMS-only contacts. In the US, many family members text via SMS (not WhatsApp), and you'll miss them if you only scan WhatsApp.

**How to connect**: Chrome → `messages.google.com`. Make sure Messages for Web is set up on your phone.

**What the exocortex needs**: Read inbox, read individual threads. (Sending is harder via web — usually not needed.)

#### Fitbit (or equivalent wearable)
**Why**: Sleep, HR, workouts feed into morning briefing context and health.md. Especially useful if your mood/energy correlates with sleep — the exocortex can flag bad sleep nights.

**How to connect**: Install the Fitbit plugin. Run `/fitbit-auth` once.

**Substitution**: Same recipe works with Whoop, Oura, Apple Watch (via Health export), Garmin. Each has its own connector.

#### Monarch Money (or financial aggregator)
**Why**: Required only for the monthly financial sweep briefing. Pulls accounts, transactions, holdings.

**How to connect**: Install the Monarch Money plugin. Run `/monarch-auth` once.

**Substitution**: YNAB, Empower (Personal Capital), Plaid-based connectors all work in principle. The recipe in `briefings/monthly-finance.md` is generic.

#### Slack / Teams
**Why**: If meaningful personal-life communication happens on work tools (a side-project Slack, a community Discord, a parent Slack). Most users skip this — keep personal and work separate.

**How to connect**: Cowork → Connectors → Add Slack.

---

## Data source priorities (in CLAUDE.md)

The CLAUDE.md defines a default priority order:

```
WhatsApp > Android Messages > Email > Tasks > Calendar > Fitness > Finance
```

This ordering matters because when the exocortex has to decide where to look first for a piece of context, it follows this list. Edit it to match your reality:

- **Founders**: Email > Slack > Calendar > Messaging
- **Students**: Messaging > Calendar > Email
- **Retirees**: Messaging > Email > Calendar

---

## Health-check protocol (Step 0.5)

Every briefing pings every connected source in parallel. The recipe:

```
For each source, run a minimal read:
- Gmail: search "is:unread" with limit 1
- Calendar: list events in next 1 hour
- WhatsApp: list_contacts with limit 1
- Tasks: navigate to tasks.google.com, screenshot
- Fitbit: get_profile
- Monarch: check_auth_status

Record each as UP or DOWN.
If any are DOWN, surface a banner: ⚠️ DEGRADED: <source>
Never block the briefing — degraded is better than missing.
```

This pattern saved us many times. Connectors drop authentication, the bridge restarts, the user revokes a token. Without the health check, briefings silently fail and you don't know why.

---

## Adding a new connector

To extend the exocortex with a new data source:

1. **Install the MCP** (or find a Chrome workflow).
2. **Test reads** manually in a Cowork session before automating.
3. **Add the source to CLAUDE.md > Data Source Priorities.**
4. **Add a health-check entry** to Step 0.5 of relevant briefings.
5. **Decide which briefings should read it** — usually morning brief, possibly evening or a domain-specific briefing.
6. **Map the fields** to memory files (e.g., new financial data → finances.md).

Test for a week before relying on it.

---

## Connectors we considered but don't recommend

**Twitter / X**: high noise-to-signal for personal life. Most users would be better off not connecting it.

**LinkedIn**: same issue. The acknowledgment loop doesn't make sense for LinkedIn-style messaging.

**Phone call logs**: privacy-invasive and platform-fragmented. Use the self-report model in CLAUDE.md instead.

**Photo libraries**: massive context cost for usually-low signal. Connect only if you have a specific use case (e.g., extracting receipts from photos for tax purposes).

---

## Cost tracking

Be aware: every briefing that scans WhatsApp + Gmail + Calendar + Tasks + DMs consumes significant Claude API tokens. The math:

- Morning briefing: ~30–80K input tokens, ~3–8K output tokens. Roughly $0.30–$0.80 per run on Claude Max.
- Evening: ~15K input, ~2K output. ~$0.15.
- Weekly: ~50K input, ~10K output. ~$0.60.
- Daily commitment-to-calendar: ~5K input, ~1K output. ~$0.05.

Total daily: ~$1.20–$1.80. Total monthly: ~$40–$55 if you're on the API directly.

On Claude Max with Cowork (most users), this is all included in the $200/mo subscription up to the usage cap. Pro is fine for one or two briefings per day; for the full suite, Max is the answer.
