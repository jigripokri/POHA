# WhatsApp Gotchas

Hard-won learnings from running WhatsApp at scale through the MCP bridge. If you connect WhatsApp, read this.

> **Recommended bridge:** a [whatsmeow](https://github.com/tulir/whatsmeow)-based (Go) MCP bridge with **native name resolution**. The store resolves contact and group-sender names natively from WhatsApp's own metadata (a multi-thousand-row name/LID map), so you no longer hand-maintain phone↔LID mappings. Most of the historical pain below — broken discovery, unresolved senders, the LID migration scramble — is gone or much reduced with a native-resolution bridge. The sections are kept (some marked *historically resolved*) so you understand the failure modes if you run a different bridge or hit an edge case.

---

## 1. `list_chats` — works with a name query, useless without one

What it does **with a query**: `list_chats(query="game")` returns the matching chat(s) with a last-message preview. Handy for "find me the Game Nights group and show what's new."

What it does **with no query**: dumps thousands of unnamed `@lid` contact-stubs — null names, null timestamps, nulls sorting first. Not useful for "what's active right now."

So:

- To find a specific group or person by name: `list_chats(query="name")` or `search_contacts(query="name")`.
- To discover which chats are *active*: `search_messages` with broad keywords (see #4 below). Don't call `list_chats` with no query and try to sort it yourself.
- To list messages in a known chat: `list_messages(chat_jid=...)` works fine.

---

## 2. `limit` and `page` must be numbers, not strings

This will fail silently:

```python
list_messages(chat_jid=..., limit="10")
```

This works:

```python
list_messages(chat_jid=..., limit=10)
```

Trips up newcomers every time.

---

## 3. Sender names mostly resolve natively now

With a native-resolution (whatsmeow/Go) bridge, `chat_name` and `sender_name` come back **populated** — both in DMs and in group threads. You generally don't have to attribute messages from content anymore.

The exceptions: a few group senders may still surface as `"Unknown"` or a bare `@lid` (a contact your store has never seen a profile/pushname for). When that happens, fall back to message content and `is_from_me` to attribute.

Use `is_from_me=True` to detect your own messages (essential for finding unanswered threads).

---

## 4. Always parallelize

Scanning 10+ groups sequentially takes 60+ seconds. Parallelize:

```
For all priority groups in CLAUDE.md, fire list_messages calls in parallel.
Same for DM contacts.
```

Modern Claude tool-use supports parallel calls. Use them.

---

## 5. The LID migration (historically resolved)

**What it was**: Around late March 2026, WhatsApp migrated DM identifiers from phone-based JIDs (`+1XXXXXXXXXX@s.whatsapp.net`) to anonymous LID-based JIDs (`XXXXXXXXXXXXXXX@lid`). The timing varied per user and per contact. On bridges without native resolution, this broke hardcoded JIDs: you'd scan a contact's old phone JID, get "no messages in last 24h," and wrongly conclude they'd gone quiet — when new messages were landing under their LID.

**Why it no longer bites you**: a native-resolution (whatsmeow/Go) store maps LIDs to real names and reconciles a contact's phone JID and LID internally. You query by name (or by the JID the store hands you) and get the full thread. **You do not need to store dual JIDs per contact, and you don't run a separate "scan both JIDs" step.** Your priority-DM table can hold a single identity per person and let the store resolve the rest.

If you run a bridge *without* native resolution, the old workaround still applies: discover a contact's current LID with `search_messages(query="<a phrase only they'd use>", limit=20)`, read the `chat_jid` off the results, and scan that. But on the recommended bridge this is rarely necessary.

---

## 6. Bridge durability — keep the bridge process alive

The MCP bridge is a long-running background process that holds the linked-device session. If it isn't running when a scheduled briefing fires, the briefing gets nothing.

Run it as a **persistent OS-managed service** that survives reboots — a Scheduled Task on Windows, a `launchd` agent on macOS, a `systemd` unit on Linux.

**The gotcha that bites overnight briefings:** a **logon-triggered** task (Windows "At log on", or a per-user agent) only starts *after a user signs in*. A machine sitting at a locked screen or the login prompt overnight never starts the bridge — so your 5am brief runs against a dead bridge and returns an empty scan that looks like "quiet night."

**The fix:** use a **startup-triggered** task configured to **"run whether the user is logged on or not"** (Windows: "At startup" + "Run whether user is logged on or not"; macOS/Linux: a system-level daemon, not a per-user agent). That survives an unattended reboot and is alive before the first scheduled briefing.

---

## 7. Bridge liveness — don't trust an empty scan

A silently disconnected bridge returns **zero messages**, which is indistinguishable from a genuinely quiet day. This is the single most dangerous WhatsApp failure mode: the briefing looks like it ran clean when it actually saw nothing.

Before you trust an empty WhatsApp result, assert the bridge is actually live:

1. **Device connected** — the bridge reports a connected/registered session (not "logged out" / "needs re-link").
2. **Recent traffic** — the store has received *at least one* message (any chat) in the last 24h.

If either check fails, treat it as a **probable bridge-down signal**, not silence. Surface `⚠️ DEGRADED: WhatsApp` in the briefing and say so plainly ("WhatsApp returned nothing and shows no traffic in 24h — likely disconnected, not a quiet day"). Wire both checks into **Step 0.5 (Data Source Health Check)** so every briefing makes this assertion before reasoning about an empty result.

Rule of thumb: **"no WhatsApp activity at all in 24h" is a red flag, not a green light.**

---

## 8. MCP config location on packaged / sandboxed desktop apps

Some desktop clients are **packaged/sandboxed** (e.g. an MSIX install on Windows, or a sandboxed Mac app). These read their MCP config from a **redirected, per-package location** — *not* the obvious `%APPDATA%` (or `~/Library/Application Support`) copy you'd expect. There is often a decoy config at the obvious path that the app **does not read**: editing it changes nothing and you'll burn an hour wondering why your new bridge entry never loads.

**The reliable move:** edit the config through the app's own **"Edit Config"** entry point (typically Settings → MCP / Local servers → Edit Config). That opens the live file the app actually loads, wherever it really lives. Only hand-edit a path on disk once you've confirmed (via that entry point) which file is the real one.

---

## 9. Group messages used to be silently dropped (now fixed)

In early 2026, some bridge builds had a config bug where group messages were filtered out as if they were status broadcasts. Symptom: group chats appeared empty even though you knew they were active.

**Fix:** the bridge should only ignore `status@broadcast`. After re-linking + a history re-sync, groups come through fine via `list_messages`. Group scanning works natively — no Chrome fallback needed.

If you fork this and find groups appearing empty:

1. Check the bridge's ignore/skip config.
2. Re-link WhatsApp.
3. Wait for full history sync.

---

## 10. Call logs (voice and video) are invisible to the MCP

The WhatsApp MCP only returns messages, not call records. There's no API for "show me my recent calls."

But call logs DO appear inline in WhatsApp Web chat threads. You can:

1. Navigate to `web.whatsapp.com` via Chrome MCP.
2. Open the relevant chat.
3. Read or screenshot to see call entries.

This matters if calling cadence is part of your relationship tracking — e.g., "I should call mom this week, when did I last call her?"

For most users, the simpler **self-report model** is better:

- The morning briefing asks "When did you last call X?" during the relationship section.
- You answer ("Sunday").
- The exocortex updates people.md with that date.
- Future briefings reason from the stored last-contact date.

Less precise but reliable and zero-effort.

---

## 11. Broadcast lists and channels

WhatsApp Channels and Broadcast lists generally don't surface in the MCP. If they're important to you, you'll need to read them manually via WhatsApp Web. Most users skip this.

---

## 12. Media handling

The MCP returns text content of messages. Media (photos, voice notes, documents) appear as placeholder entries like `[Photo]` or `[Voice note]`.

You generally don't need media for personal-AI use cases — the exocortex reasons about messages, not images. If you need media access, use Chrome → WhatsApp Web.

---

## 13. Disappearing messages

If a chat has disappearing messages enabled (e.g., a private parent chat with 24-hour disappearing), only messages currently visible to your WhatsApp client are scannable. Once they disappear from your app, they're gone from the MCP too.

For high-trust groups with disappearing messages, factor this in: the exocortex won't have continuous memory of those conversations. Important commitments from those chats should be transferred to `commitments.md` immediately.

---

## 14. Don't try to spoof your number

The MCP bridge uses your real WhatsApp account. Don't try to attach a different number, run multiple sessions, or do anything weird. WhatsApp's anti-abuse systems will flag and potentially suspend the account.

---

## 15. Rate limits

WhatsApp has un-documented per-account rate limits. If you scan aggressively (e.g., every 5 minutes against 100 groups), you may hit them.

The default scheduled briefings (morning + evening + weekly) don't come close. Don't go crazier than that without testing.

---

## Summary checklist

When connecting WhatsApp:

- [ ] Use a native-resolution (whatsmeow/Go) bridge so names and LIDs resolve automatically
- [ ] Install the bridge as a **startup-triggered**, "run whether logged on or not" service so overnight briefings survive a reboot
- [ ] Wait for full history sync (10–30 min) before running briefings
- [ ] Assert bridge liveness (connected + traffic in 24h) before trusting an empty scan
- [ ] Edit MCP config via the app's "Edit Config" entry point if the client is packaged/sandboxed
- [ ] Use `list_chats(query=...)` / `search_contacts` to find chats by name; `search_messages` to discover active ones
- [ ] Parallelize all reads
- [ ] Pass numeric `limit` and `page` params
- [ ] Use `is_from_me` to detect unanswered messages
- [ ] Use the self-report model for call-cadence tracking
- [ ] Fall back to message content on the rare group sender that still shows "Unknown"
