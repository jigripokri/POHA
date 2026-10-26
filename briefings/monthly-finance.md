# Monthly Financial Sweep

**Schedule:** `0 6 28 * *` (28th of each month, 6am)
**Output:** Two emails — full financial brief to user, credit card sweep to user + partner (if applicable).

Pulls financial data once and runs five analyses: spending autopsy, net worth update, subscription audit, credit card optimization, and financial insights.

---

## Prompt

```
You are running the monthly financial sweep for {{USER_NAME}}. This briefing is sensitive — read memory/finances.md, never quote it outside the email.

## Step 1 — Memory load

Follow the **Open** steps in [`_memory-contract.md`](./_memory-contract.md): read `memory/INDEX.md` first, then only what this briefing's row in `INDEX > Read plan` marks `full`; everything else by section or grep. For this briefing: memory/INDEX.md and memory/finances.md in full. Past money insights: `grep -n -E "subject: #(money|fire|subs)" memory/insights.md` and the same grep on this quarter's `memory/archive/insights/` file.

## Step 2 — Pull live data

From Monarch Money (or whatever your financial connector is):
- Accounts (current balances)
- Transactions (this month)
- Budgets (this month vs target)
- Cashflow (this month vs avg)
- Holdings (current positions)

DO NOT proceed if Monarch is unreachable — flag in a degraded email and stop.

## Step 3 — Analysis 1: Spending autopsy

Categorize this month's transactions:
- By category vs last month, vs 3-month avg
- Flag any category that's >30% above 3-month avg
- Identify top 5 individual transactions
- Catch unusual merchants (first-time purchases over $200)

## Step 4 — Analysis 2: Net worth update

Compute:
- Current NW from accounts + holdings + property estimates from finances.md
- Delta vs last month
- Delta vs 12 months ago
- Update finances.md > Snapshot section with new values + date

## Step 5 — Analysis 3: Subscription watchdog

Identify recurring transactions (same merchant, same amount, monthly cadence).
For each:
- Is it in finances.md > Subscriptions list?
- If not, flag as NEW
- If marked "cancel" in memory, flag as STILL ACTIVE
- Compute annualized cost

## Step 6 — Analysis 4: Credit card optimization

For each active card (from finances.md > Credit cards):
- Was the spend this month optimal? (e.g. spent on Card A when Card B has higher rewards for that category)
- Are annual fees coming up in the next 90 days?
- Are there sign-up bonus opportunities relevant to upcoming planned spend?

## Step 7 — Analysis 5: Financial insights

One or two non-obvious observations. Examples:
- "Travel spend is up 40% YoY — is this a new pattern?"
- "Cash position has grown to <X> — sitting in checking, not earning"
- "Property X's rent hasn't increased in 18 months; market rate suggests +<Y>%"

## Step 8 — Compose Email 1 (full brief)

To: {{USER_EMAIL}}
Subject: 💰 Monthly Financial Sweep — <month, year>

Sections:
1. 📊 Net worth: $X (Δ vs last month: +/-$Y)
2. 🛒 Spending vs avg (top 3 deltas, with explanation)
3. 📺 Subscription review (anything to cancel?)
4. 💳 Credit card optimization (if action needed)
5. 🧠 Insight (1-2 non-obvious patterns)
6. ✅ Action items (with mailto: links)

## Step 9 — Compose Email 2 (credit card sweep, optional)

If you share finances with a partner and want them in the loop on cards specifically:

To: {{USER_EMAIL}}, {{PARTNER_EMAIL}}
Subject: 💳 Credit card check — <month>

Sections:
1. Recent transactions worth flagging
2. Annual fees coming up
3. Any benefits expiring (e.g. travel credits, anniversary points)

## Step 10 — Update memory

Update finances.md > Snapshot with new NW.
Update finances.md > Credit cards if any changes (new cards, cancellations).
Insight: run the novelty gate on the best candidate (`memory_maint.py novelty --subject "#money" …`). Novel and subject below cap → one new lens; near-duplicate → `evidence: +1`. Max one new lens per run.
Add cancel-this-sub action items as new rows in commitments.md (`next-id C`).
Journal: ≤6 `fact` lines (net worth, spend status, new subscriptions) + one `review` entry tagged #money.
Then the **Close** steps in [`_memory-contract.md`](./_memory-contract.md): save the briefing, update line-3 headers, `memory_maint.py run-note`, `memory_maint.py all --job finance`.

Confirm with: "Financial sweep complete. NW: $X. <N> action items. <M> subscriptions flagged."
```

---

## Customization notes

- **This briefing is the most sensitive.** Double-check `.gitignore` excludes `memory/` before you run it.
- **The 28th is opinionated.** Most months it's before the next billing cycle, which is when you want to catch subscriptions. Some months it's the day before. Adjust.
- **Don't share financial briefings with anyone but explicit trusted recipients.** The default partner-CC for credit card sweep assumes high trust.
- **If you don't use Monarch, swap the data source.** Plaid, YNAB, Empower, manual entry — same recipe, different inputs.
