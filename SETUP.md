# Setup

End-to-end walkthrough. Plan ~3 hours for honest setup, ~30 minutes for a minimal version.

---

## 0. Prerequisites

- A computer (Mac, Windows, or Linux)
- A Claude Pro or Max subscription ([signup](https://claude.ai))
- A primary email account you can send to yourself (Gmail recommended — the acknowledgment loop is built around it)
- Calendar, messaging apps, and tasks tools you want connected

---

## 1. Install Claude Desktop with Cowork mode

1. Download [Claude Desktop](https://claude.ai/download).
2. Sign in.
3. Enable Cowork mode in settings (Research Preview feature — request access if not already enabled).

Cowork mode is what gives Claude access to a folder on your computer, scheduled tasks, and MCP connectors. Without it, this won't work.

---

## 2. Clone this repo

Pick a stable folder on your machine — somewhere you won't accidentally delete. Examples:

- macOS / Linux: `~/exocortex`
- Windows: `C:\Users\<you>\exocortex`

```bash
git clone https://github.com/<your-username>/exocortex.git ~/exocortex
cd ~/exocortex
```

If you're forking from the canonical repo, do that first on GitHub, then clone your fork.

---

## 3. Mount the folder in Cowork

In Claude Desktop:

1. Start a new Cowork session.
2. When prompted to select a folder, choose your `exocortex/` clone.
3. Confirm Claude can read and write to it.

Claude now has access to all the files in this repo.

---

## 4. Fill in `CLAUDE.md`

Open `CLAUDE.md` in any editor. It's the persona + ruleset that drives every output.

Look for these placeholders and replace them with your own values:

| Placeholder | Replace with |
|-------------|--------------|
| `{{USER_NAME}}` | Your name |
| `{{USER_EMAIL}}` | Your primary email (also where briefings go) |
| `{{PARTNER_NAME}}` | Spouse / partner name, or remove the line |
| `{{CHILDREN}}` | Comma-separated kid names + ages, or remove |
| `{{LOCATION}}` | City you live in |
| `{{TIER_1}}`, `{{TIER_2}}`, `{{TIER_3}}` | Your priority tiers (what actually matters) |
| `{{TRACKED_PROJECTS}}` | 1–3 long-running projects the exocortex should always surface |

Also customize:

- **Persona section.** Default is "direct, warm, slightly cheeky chief of staff." Change the adjectives if you want softer or more sarcastic.
- **Messaging platform rules.** If your partner texts via SMS not WhatsApp (or vice versa), note it here.
- **Calendar event rules.** Anything Claude should never do (e.g., "never create events before 7am" or "always block 6pm for family dinner") goes here.

The rest of `CLAUDE.md` is generic and should work as-is.

---

## 5. Connect the MCPs you want

Three tiers of recommended connections. Start minimal; add more later.

### Minimum viable exocortex (do these first)

1. **Gmail** — The acknowledgment loop runs through email. Non-negotiable.
   - In Cowork → Connectors → Add Gmail
   - Authorize with the same email account you use for `{{USER_EMAIL}}` in CLAUDE.md.

2. **Google Calendar** — Where commitments turn into events.
   - Connectors → Add Google Calendar
   - Use the same Google account as Gmail.

### High-leverage adds (do these next)

3. **WhatsApp** — Most personal life lives here for non-US users.
   - Connectors → Add WhatsApp
   - Scan the QR code with WhatsApp on your phone.
   - Wait for full history sync (can take 10–30 minutes).

4. **Google Tasks** — Source of truth for "what I need to do today."
   - No native MCP yet. The exocortex accesses Tasks via Chrome → `tasks.google.com`.
   - Make sure you have Claude in Chrome installed and logged into your Google account.

### Domain-specific adds (optional)

5. **Google Health** — For the health surfaces (morning chip, weekly section, monthly memo) and `health.md`.
   - Install the Google Health plugin.
   - Run its OAuth flow once (read-only scopes); tokens are stored locally. Briefings then call the health MCP directly — no sync script.
   - Using Whoop / Oura / Apple Health / Garmin instead? Same recipe — swap the connector. See [`docs/health-system.md`](./docs/health-system.md).

6. **Monarch Money** — For the monthly financial sweep.
   - Install the Monarch Money plugin.
   - Run `/monarch-auth` once to authorize.

7. **Android Messages** — If anyone important texts you via SMS.
   - Accessed via Chrome → `messages.google.com`.
   - Make sure Messages for Web is set up on your phone.

---

## 6. Bootstrap memory

This is the part that takes time. You're going to spend 90 minutes telling Claude about your life.

Tell Claude:

> *"Read CLAUDE.md and ARCHITECTURE.md. Then walk me through filling in the seven memory files. Start with people.md — ask me questions to populate it. Move on to the next file when I say so."*

Claude will ask you questions like:

- *Who are the 10–20 most important people in your life right now?*
- *What's an open thread with each of them — something unresolved, a follow-up you owe, an event coming up?*
- *What are your top 3 priorities this quarter?*
- *What's an insight about your life nobody else would notice?*

Answer honestly. The exocortex is only as good as the texture you give it.

Files to populate, in order:

1. `memory/people.md` — relationships
2. `memory/commitments.md` — open promises (start with whatever you can remember)
3. `memory/life.md` — goals + priorities
4. `memory/insights.md` — start empty, will fill up over time
5. `memory/finances.md` — only if you want financial sweeps (optional, sensitive)
6. `memory/health.md` — only if you want health context (optional, sensitive)
7. `memory/private/carry-on.md` — leave empty for now; load only when needed

Each template has section headers and an example entry. Don't aim for completeness on day one — aim for the 20% that captures 80% of what matters.

---

## 7. Set up scheduled tasks

Once memory is bootstrapped, wire up the scheduled tasks:

Tell Claude:

> *"Set up the scheduled tasks defined in BACKLOG.md. Use the prompts in briefings/. Confirm each cron schedule before creating."*

Claude will create:

- Morning brief: `0 5 * * *` (5am daily)
- Evening reflection: `0 21 * * *` (9pm daily)
- Weekly review: `0 9 * * 0` (Sunday 9am)
- Commitment → Calendar: `0 7 * * *` (7am daily)
- GSD Friday: `0 12 * * 5` (Friday noon)
- Weekend Fun Finder: `0 12 * * 5` (Friday noon)
- Monthly finance: `0 6 28 * *` (28th of each month, 6am)
- Monthly health memo: `0 7 28 * *` (28th of each month, 7am)
- Bloodwork reminder: twice yearly, the month before each draw (set your two draw months — e.g. `0 8 1 3,9 *` for Mar 1 & Sep 1)

You can adjust times to match your schedule. The morning brief should land before your alarm goes off.

---

## 8. Test the loop

Before going to bed, run the morning brief manually:

> *"Run the morning briefing prompt now. Send the email to {{USER_EMAIL}}."*

Check the email when it arrives. Look for:

- ✅ Step 0 ran (Acknowledgment scan reported "no signals" — that's correct, since you haven't tapped any links yet)
- ✅ Step 0.5 ran (Data source health check shows all UP)
- ✅ Action items have one-tap "I did this" links
- ✅ Memory was updated

Tap one of the acknowledgment links. Wait until the next briefing runs. Verify the corresponding commitment moved to ✅ Done.

If the loop closes — congratulations, your exocortex is live.

---

## 9. Iterate

Week 1: just observe. Don't change anything. Notice what's noise, what's signal, what's missing.

Week 2: tune. Edit `CLAUDE.md` to filter the noise. Add memory entries for the things you keep having to re-explain. Adjust scheduled task timings.

Week 3+: extend. Add a new briefing for something specific to your life. Write a new skill. Connect a new data source.

The exocortex compounds. Month 1 it's useful. Month 6 it's hard to live without.

---

## Troubleshooting

**Briefing didn't run at the scheduled time.**
Cowork needs the Claude Desktop app to be running (or your machine needs to be awake) when scheduled tasks fire. Check that the app is open and you're signed in. If you sleep your laptop, briefings won't run until you wake it.

**Briefing ran but the email is empty / short.**
Check `Step 0.5 — Data source health check` in the email. If anything is DEGRADED, that connector is broken. Reauthorize it in Connectors.

**Acknowledgment loop isn't closing.**
Check Gmail search: `subject:EXO_DONE`. Are the emails there? If yes, but commitments aren't getting marked done, the issue is slug-matching in the briefing prompt. Tell Claude: *"Show me the latest EXO_DONE emails and walk me through why they didn't match commitments.md."*

**Memory files keep getting longer.**
Run the weekly review religiously. The 3-week rule is what keeps memory tight — items older than 3 weeks without reference should be archived. If weekly review isn't pruning aggressively enough, edit `briefings/weekly-review.md` to be more aggressive.

**Claude is using the wrong voice in drafts.**
Edit `skills/draft/SKILL.md`. Add specific examples of your voice. The more example pairs (situation → how you actually replied), the better the mirror.

---

## What to do next

Once the basics work, see [`docs/customization.md`](./docs/customization.md) for ideas on extending. The biggest single win for most people is adding a per-person memory file (`memory/<person>.md`) for someone they need to track ongoing context on — a kid, an aging parent, a high-touch report.
