# Weekend Fun Finder

**Schedule:** `0 12 * * 5` (Friday noon — same time as GSD, separate task)
**Output:** Email with curated weekend activities scored against your household's preferences.

Searches for local events and scores them through multiple lenses (yours, your partner's, your kids') so the family has a curated short-list by Friday afternoon.

---

## Prompt

```
You are running the weekend fun finder for {{USER_NAME}}.

## Step 1 — Load preferences

Read `memory/weekend-prefs.md` if it exists. Otherwise infer from people.md and life.md (interests, kids' ages, recent activities).

Capture for each household member:
- Activity types they enjoy
- Activity types they don't
- Energy level on weekends (high-energy adventure vs chill at home)
- Travel radius (5 mi / 30 mi / day trip)

## Step 2 — Search for events

Use WebSearch for:
- Local events this Saturday + Sunday in {{LOCATION}}
- Sources: city event sites, Eventbrite, local parent groups, museums, parks, sports

Sources vary by region. For US users:
- "<city> events this weekend"
- "<city> kids activities"
- "<city> outdoor events"
- "<city> farmer's market"

For non-US users, swap in equivalent local sources.

Cast a wide net — 30-50 candidates.

## Step 3 — Score each candidate

For each candidate, score through 3 lenses (or however many household members you're scoring for):

| Lens | What it values |
|------|----------------|
| Kid (if applicable) | Interactive, age-appropriate, has-other-kids, learn-something |
| Partner | Aesthetic, calm-or-energetic-per-prefs, social, novel |
| {{USER_NAME}} | Per your stated values in life.md |

Each lens scores 1-5. Total = sum.

## Step 4 — Cluster and rank

Bucket into:
- **Top 5 family picks** (high score across all lenses)
- **Top 3 per person** (high in that person's lens, may not be a family fit)
- **Day trip option** (one bigger adventure if energy is high)

## Step 5 — Compose the email

Subject: 🌅 Weekend plans — <Sat date> – <Sun date>

Sections:
1. 🏆 Top 5 family picks (with: name, time, location, why it scores, link to register)
2. 👤 {{USER_NAME}}'s top 3 (likely solo or with partner)
3. 👤 {{PARTNER_NAME}}'s top 3
4. 👤 {{KID_NAME}}'s top 3 (if applicable)
5. 🚗 One day-trip option (if anything caught your eye for a bigger adventure)
6. 🍽️ Restaurant suggestion (one place you've been talking about trying)
7. 🌧️ Backup if weather's bad

Each event gets a `mailto:` "✅ Let's do this" link to capture commitment.

## Step 6 — Update memory

If a "let's do this" comes in via Step 0 of next morning's brief, add the event as a new row in commitments.md (`next-id C`, State CALENDAR NEEDED).
Past picks for de-duplication: `python3 tools/memory_maint.py lookback --tag "#weekend" --days 28`. Write one journal `sent` line tagged #weekend with the top family pick.
Then the **Close** steps in [`_memory-contract.md`](./_memory-contract.md): save the briefing, update line-3 headers, `memory_maint.py run-note`, `memory_maint.py all --job weekend`.
```

---

## Customization notes

- **The preference files matter most.** Spend 20 min populating `memory/weekend-prefs.md` for each household member.
- **Scoring is approximate but useful.** It's mostly to filter — the email is the curation.
- **If you're not in the US**, replace search sources with your country/city's equivalents and tell the exocortex via CLAUDE.md.
