# The Health System

How the exocortex turns a continuous wearable stream into something useful — without burying you in numbers.

> **Data source:** [Google Health](./data-sources.md#google-health-or-equivalent-wearable-platform) (or any equivalent — Whoop, Oura, Apple Health, Garmin). Briefings call the health MCP tools directly. There is no sync script.

---

## The core principle: daily health data is mostly noise

Your resting heart rate is 52 today and 54 yesterday. So what? A single day's numbers tell you almost nothing — they're dominated by measurement noise, a late coffee, a bad night's sleep, the room temperature.

**The signal lives in deviations from your own baseline**, observed at the cadence each metric actually carries information at. Sleep matters daily. Resting HR matters as a weekly trend. VO₂ max matters as a monthly trajectory. Dumping all of it into every briefing trains you to ignore the briefing.

So the exocortex surfaces each metric **only at the altitude where it means something**, and never just reports a number — it always implies an action.

---

## The four surfaces

### 1. Morning brief health chip — conditional and silent by default

The morning brief is the daily surface, so it must be ruthless. The health chip is **omitted entirely** on a normal day. It fires **only** when a deviation trigger trips:

- Sleep below a floor (e.g. < 6h, or a sleep-score collapse)
- Resting HR above baseline + ~5 bpm
- HRV down meaningfully vs the 7-day average
- Multiple consecutive days of zero Zone-2 (cardio) minutes
- A weight spike outside normal day-to-day variance

When it fires, it **never dumps numbers** — it states the deviation in one plain line and implies the action: *"Your resting heart rate is running 6 bpm high for the third day — you're either fighting something off or under-slept. Ease off the hard workout today."* Plain language, not doctor-speak. If nothing trips, the chip doesn't appear.

### 2. Weekly email health section — always present

The Sunday weekly review **always** includes a compact health section. About six numbers, a pattern, and one action:

- Resting HR Δ (vs prior week)
- Zone-2 minutes vs target
- Sleep average + variance
- HRV trend
- Step consistency (how many days hit the floor)
- Smoothed weight Δ

Then **one pattern** ("you sleep 40 min less on nights after evening workouts") and **one action** ("move the Thursday session to morning"). Six numbers is the cap — the weekly is a trend check, not a data dump.

### 3. Monthly Health Memo (the 28th)

The deep pass. ~250 words, prose not tables, covering:

- **Vitals trajectory** — RHR floor, HRV, weight, VO₂ max over the month
- **Training load** — Zone-2 minutes vs target, consistency
- **Sleep architecture** — duration, variance, what's drifting
- **Genetic-context flags** — if you've stored risk priors (see below), cross-reference the month's trends against them
- **Pre-bloodwork prep (twice a year)** — in the month *before* each scheduled draw, a section mapping the wearable trends to a doctor ask-list so you walk in with questions, not just numbers

Full spec in [`briefings/monthly-health.md`](../briefings/monthly-health.md).

### 4. `health.md` — auto-updated by the briefings

The memory file is kept current automatically:

- **Latest daily** snapshot written by the morning brief
- **Rolling weekly** trends written by the weekly review
- **Rolling monthly** trajectory written by the monthly memo

You rarely hand-edit the data sections; you hand-edit the *context* sections (concerns, doctors, family history, genetic priors) the wearable can't know.

---

## Cadence table — what matters at which altitude

| Metric | Daily (morning chip) | Weekly section | Monthly memo | Why |
|--------|:--------------------:|:--------------:|:------------:|-----|
| **Sleep duration / score** | ✅ on deviation | ✅ avg + variance | ✅ architecture | Acute — a bad night changes *today*. |
| **Resting HR** | ✅ if > baseline+5 | ✅ weekly Δ | ✅ floor trajectory | Noisy daily; clean as a weekly/monthly trend. |
| **HRV** | ⚠️ only on sharp drop | ✅ trend | ✅ trajectory | Day-to-day swings are mostly noise. |
| **Zone-2 / cardio load** | ✅ if multi-day zero | ✅ vs target | ✅ load trend | Behavior you can correct this week. |
| **Steps** | — | ✅ consistency | ✅ trend | Only the pattern matters, not the daily count. |
| **Weight** | ✅ only on spike | ✅ smoothed Δ | ✅ trajectory | Daily weight is water; smoothed weight is signal. |
| **VO₂ max** | — | — | ✅ | Moves too slowly to mean anything sub-monthly. |
| **Body fat** | — | — | ✅ | Same — a monthly trajectory metric. |

The pattern: **acute, behavior-correctable metrics surface daily; slow-moving trends surface monthly; weekly is the in-between trend check.**

---

## Wearable-compliance caveat (suppress on low data)

Every metric above assumes you actually *wore the device*. When valid-data days drop below **~80% of the week**, the other metrics become unreliable — a "resting HR spike" might just be three days you didn't wear the watch.

So the health surfaces **auto-suppress when compliance is low**: if the week has too few valid-data days, don't report a spurious trend. Instead, the only health note is a quiet nudge to wear the device, and the numeric sections are skipped until data quality recovers. A confident-sounding trend computed from three data points is worse than no trend.

---

## Why this is non-blocking

Health is the **lowest-priority input** in the stack. It is never worth failing or delaying a briefing over. If the health MCP is unreachable, the briefing proceeds silently with no health surface, and only after **multiple consecutive down-days** does it raise a `⚠️ DEGRADED: health` note (see [`data-sources.md`](./data-sources.md#tier-3--domain-specific)). A single transient disconnect should generate zero noise.

---

## Optional: the genetic-context layer

If you have genome data (a consumer DNA report, a clinical panel), you can give the health surfaces a fixed layer of **risk priors** to reason against — read on *every* health surface, not just the monthly memo.

How to wire it, safely:

- Store **risk priors only** in `health.md` — short, plain-language statements of *which signals matter most for you and why* (e.g. "elevated clotting risk → watch recovery and hydration around long-haul flights"; "lipid-sensitive → weight up + training down is a bigger deal than for most"). **Do not paste raw reports, variant IDs, or clinical findings into the repo.** The repo is your operating layer, not your medical record.
- Have each surface **cross-reference** the priors against live data. Two patterns this enables:
  - **Event-triggered protocols.** The morning brief can read a prior plus today's calendar — e.g. a clotting-risk prior + a flight over ~6h on the calendar → surface a movement/hydration protocol and watch recovery metrics for a few days after.
  - **Weighted interpretation.** The same RHR or weight drift means more (or less) depending on your priors — the monthly memo surfaces the priors the month's data actually touches, and stays quiet on the rest.

The principle: the genome sets the *priors* (what to watch), the bloodwork is the periodic *ground truth*, and the wearable is the *continuous drift signal* between draws. Surfaces read all three. This layer is entirely optional — with no genetic data stored, every surface simply skips it.

> **Privacy:** genetic data is among the most sensitive you have. Keep priors in `health.md` (which `.gitignore` excludes by default), never in any outbound email, and never in a public fork.

---

## Earned praise / the positive-signal system

The surfaces don't only warn — they **encourage when things go right.** But praise is rationed as carefully as the alerts, because empty "good job" erodes the warnings: if the system congratulates you for nothing, you stop trusting it when it raises a real flag.

So praise must clear a real bar:

- **A genuine milestone** — a streak hit, a target met, a sustained good trend (not a single good day).
- **Specific, not generic.** Name the behavior *and* its payoff ("eight straight days hitting your Zone-2 target — that's the work that drops your resting HR floor"). Never a bare "nice job."
- **Scarce.** At most **one** praise line per email, and never an alert and praise in the same surface. Daily praise should be rarer still — roughly once a week at most.

**The all-green month.** When a whole month clears the bar with nothing to fix, the monthly memo should *not* produce a wall of green checkmarks — that's just noise in a different color. Instead it **pivots from metrics to purpose**: it points at your health north-star — the reason the training matters to you (the activity you want to keep doing for decades, the people you want to keep pace with, the life you're training for) — rather than reporting another good number. A clean month is exactly when to reconnect the work to the why.

This is referenced operationally in [`briefings/morning-brief.md`](../briefings/morning-brief.md) (Step 8), [`briefings/weekly-review.md`](../briefings/weekly-review.md), and [`briefings/monthly-health.md`](../briefings/monthly-health.md).
