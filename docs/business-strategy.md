# PrepCast — Product & Business Strategy

Working doc for scaling PrepCast beyond a single-restaurant portfolio demo into a real
multi-product consulting/software business. Not a single-founder freelance plan — assumes a
small team (Rishi + trusted collaborators) as the project grows.

**Status:** strategy/planning stage. Nothing here is built yet except the core PrepCast
forecasting pipeline (see main README.md and docs/methodology.md for the technical product).

---

## 1. Success metrics — how a restaurant owner judges "is this useful"

Owners think in money, waste, and whether their own staff trust the tool — not in model
accuracy stats. Three tiers, in order of what actually drives a sale/renewal:

### Tier 1 — Money metrics (closes the deal, drives renewal)

| Metric | Why it matters |
|---|---|
| Food cost % of revenue (before vs. after) | Already tracked by every F&B owner monthly — plug into their existing mental model, don't invent a new one |
| Waste cost (SAR/month) and waste weight (kg/month) | Directly reduces COGS, easy to show as a before/after delta |
| Stockout-driven lost sales (SAR/month) | Most owners don't measure this today at all — showing it for the first time is often the "aha" moment that sells the pilot |
| **Net savings** (waste avoided + lost sales avoided) vs. their own historical baseline | The single number that goes in a renewal conversation |

### Tier 2 — Operational trust metrics (determines renewal more than the headline SAR number)

| Metric | Why it matters |
|---|---|
| Forecast accuracy, translated into kitchen-relevant language | Not "33% WAPE" — say "the prep list was within 1 portion of actual demand on 70% of dish-days" |
| Manual override rate | How often kitchen staff ignore the suggested prep list and go with gut feel — high override = low trust, even if backend numbers look good |
| Time saved on manual prep planning per week | Softer cost, but real (sous chef / manager time) |

### Tier 3 — Leading/adoption indicators (catch problems before they hit Tier 1 numbers)

- % of days the prep list was actually used as-is (not ignored)
- Staff qualitative feedback / satisfaction pulse
- Stability of the saving month to month (one-off lucky stretch vs. a real, repeatable effect)

### How to validate a pilot's results (avoid fooling yourself or the client)

- Compare against the **same period last year**, not just last month — controls for seasonality
- Where possible, run a **holdout comparison**: PrepCast on part of the menu/days, old method on
  the rest, in the *same* time window, so results aren't contaminated by different external
  conditions
- Run the pilot long enough to cross at least one "hard" period (a holiday, a slow month) before
  claiming a stable result — 2 calm weeks proves much less than 6-8 weeks of normal variation

---

## 2. Positioning — not competing with Oracle/Fourth on day 1

**Strategy:** don't try to out-build enterprise suites immediately. Prove the product is useful
and trustworthy on small/independent restaurants first, and treat "worth being considered as a
replacement by an existing Oracle/Foodics/Fourth user" as a multi-year destination, not a launch
requirement.

**Path to that destination (roughly in order):**
1. Prove value on real, paying (or at least real-data) pilots — this is the non-negotiable first
   step; nothing below matters without real customer proof
2. Add support, account management, and a real support line as soon as there's more than a
   couple of paying clients — don't over-build this before anyone needs it, but don't skip it
   once clients expect it
3. Pursue a security certification (e.g. SOC2-equivalent) once handling real POS/financial data
   at any meaningful scale — a prerequisite for larger buyers, not an early-stage requirement
4. Accumulate real-world edge cases and features over time from actual customers (multi-currency,
   supplier substitutions, menu complexity, etc.) — this is what makes enterprise tools strong,
   and it only comes from volume and time, not more code written in isolation
5. Target a POS integration (Foodics is the natural first choice regionally) once there's
   repeat demand for it — this is a serious engineering investment, don't build it speculatively

**Realistic near-term target market:** independent restaurants and small 2-5 location groups
that are currently underserved — too small/price-sensitive for Oracle, often running Foodics or
nothing configured well, with nobody translating their data into decisions. This is a real,
immediately monetizable gap, not a lesser substitute for "real" enterprise sales.

---

## 3. MenuMatrix + PrepCast combined pitch

**Why combine them:** they answer two different, sequential questions an owner actually asks:
- MenuMatrix: "which dishes make me money?" (profitability per item — price vs. food cost vs.
  volume, menu engineering quadrant analysis)
- PrepCast: "how much of each dish should I make tomorrow?" (demand forecast → prep list)

**Sales flow:** show the owner which items are quietly losing money or barely selling first
(MenuMatrix), then show how to stop over/under-prepping on the items worth keeping (PrepCast).
Combined pitch: "I'll tell you what to sell, how to price it, and how much to make" — a complete
menu-economics story instead of two disconnected tools.

**Real technical synergy (future, not day-1):** MenuMatrix's profitability score could feed
PrepCast's prep buffer logic directly — e.g. prep a thinner safety margin on low-margin items,
a fatter one on proven "stars." Worth building once there's a real client to validate it against,
not before.

**Sequencing note:** sell as a bundle conceptually first (two tools, one engagement, one combined
report). Don't over-invest in a deep technical merge before a client has paid for it.

---

## 4. Labor scheduling — to design and build later

**Core idea:** once covers are forecasted per shift/hour, recommend staffing levels instead of
owners scheduling from habit. Labor is typically 25-35% of revenue — one of the largest
controllable costs in F&B, and a bigger pain point for many owners than food waste.

**Basic calculation approach (draft, needs real validation per restaurant type):**
1. Forecast covers per shift/hour (needs an hourly/daypart breakdown — PrepCast's existing
   lunch/dinner/late daypart structure is a starting point, not yet sufficient)
2. Convert covers to required labor via a **covers-per-labor-hour ratio** per role (servers,
   kitchen line, hosts) — a standard F&B KPI, but the ratio itself must be set per restaurant,
   not assumed globally
3. Apply **role-specific minimums** regardless of volume (always need ≥1 chef, ≥1 cashier, etc.)
   as a floor constraint on top of the ratio
4. Output: a suggested staffing grid per shift per role, compared against the restaurant's actual
   schedule to show over/understaffing gaps in SAR

**Why restaurant type changes everything — this can't be one generic model:**

| Type | Key difference |
|---|---|
| Fast casual | Short service time, high throughput — labor ratio fairly predictable from covers alone, closest to PrepCast's current modeling style |
| Fine dining | Low covers-per-server ratio (high-touch service); course-paced timing matters more than raw covers; relationship is far less linear — a slow night still needs a full team for the guests present |
| QSR / counter-service | Staffing to a queue-length/wait-time SLA target, not a covers ratio |
| Hotel F&B | Multiple outlets, banquet/event spikes layered on regular covers — far more volatile and lumpy than a single restaurant |

**Why this is a real advantage for us specifically:** this needs genuine hands-on hospitality
operations knowledge (fine dining vs. casual vs. hotel F&B each need different logic) to get
right — a pure software team without that background would likely build one generic model and
get it wrong for half their target market.

**Build sequencing:** only start building this once the core covers-forecasting product (PrepCast)
is validated on at least one real pilot — reuses the same forecasting core, so it's a natural
second product, not a rebuild.

---

## 5. POS health check — the low-commitment first engagement

**What it is:** a diagnostic, not a sale. Pull a few months of a restaurant's actual POS export
(sales by item/day/hour) and surface operational red flags, without needing to build or sell
anything yet. This is the easiest, lowest-build-cost way to start a real conversation with a
real owner using their own numbers.

**What to look for:**
1. **Waste/stockout patterns** — frequent 86'd items, or sudden sales drop-offs on popular items
   that suggest unrecorded stockouts
2. **Menu mix skew** — a small number of items driving most revenue, many items selling almost
   nothing (dead menu weight — inflates prep complexity and inventory cost for little payoff)
3. **Day-of-week / time-of-day demand volatility** — how much real swing exists between peak and
   trough; tells you how much a forecasting tool would even help this specific restaurant (a very
   flat, predictable business has less to gain)
4. **Discounting/comp patterns** — excessive discounts can signal service-recovery issues or
   demand mismatches (over-prepped, discounting to avoid waste)
5. **Labor cost ratio vs. revenue**, if payroll data is available — shows structural
   overstaffing independent of any forecasting fix

**How to validate findings before presenting them as fact:**
- Cross-check every finding against what the **owner/manager already believes.** If the data
  says "Tuesdays are consistently 40% below other weekdays" and they confirm it from the floor,
  that's validated. If they're surprised, dig deeper before presenting it — POS data has real
  quirks (manual comps, misc categories, void handling) that can mislead at face value
- **Triangulate with a second data source** where possible — inventory/waste logs, supplier
  invoices, staff schedules. POS alone can mislead (e.g. a stockout often just looks like "zero
  sales," indistinguishable from genuine zero demand, without a second signal)
- Keep the first pass **qualitative and conversational**, not a definitive report — frame as
  "here's what the data suggests, does this match the floor?" Builds trust; avoids overclaiming
  from one noisy dataset

**Why this is the right first product:** lowest build effort (pure analysis, no deployment
needed), uses skills already in hand, and is the natural on-ramp into pitching MenuMatrix /
PrepCast once a real problem has been shown using the owner's own numbers.

---

## 6. Ops bot — daily delivery via WhatsApp/Telegram

**Core idea:** don't make owners/managers log into a dashboard (friction, another login, another
habit to build) — push the same information where they already operate: WhatsApp or Telegram,
near-universal for business communication in this region.

**What it does (v1, concrete):**
- **Morning push:** "Today's forecast: 290 covers (+12% vs last Tuesday). Prep list attached." —
  the PrepCast output delivered automatically, no login required
- **Threshold alerts:** e.g. "Grilled salmon trending 30% above forecast today — consider extra
  prep" — an intraday nudge if actual sales deviate from forecast mid-shift
- **Weekly digest:** Friday summary — waste/stockout numbers for the week, trending dishes, a
  simple "you saved X SAR this week vs. your usual method." This doubles as the ongoing
  proof-of-value mechanism that justifies continued payment

**v2 (later, not day one):** two-way interaction — manager replies "busy tonight, private event"
and the bot adjusts the next prep suggestion.

**Why it matters beyond convenience:**
- Turns a one-time software delivery into a **recurring, visible touchpoint** — a real reason to
  charge monthly instead of a one-off project fee
- The weekly "you saved X" message is effectively a sales pitch running on autopilot, continuously
  demonstrating value without a manual check-in
- Low incremental build cost — the forecast and savings numbers already exist; a bot is a
  delivery mechanism (Telegram Bot API / WhatsApp Business API) wrapped around existing output,
  not new modeling work

**Team fit:** this is a good place to bring in a second person (per the "not a solo freelancer"
point) — messaging API integration and uptime for a bot that owners depend on daily is a natural
place to split responsibility rather than Rishi owning everything solo.

---

---

## 7. Pricing model (decided 2026-10-16)

**Decision: flat monthly fee, tiered by restaurant size/complexity — not a percentage of
revenue or savings.**

**Why not a revenue/savings percentage:** requires ongoing access to the restaurant's real
financials, creates constant dispute-prone attribution ("did we actually cause this gain?"),
and is operationally heavy to administer and verify.

**Why a flat tiered fee:** it's how Foodics, Toast, and essentially every SMB restaurant-tech
vendor already prices — owners already understand this model, so we're not asking them to learn
a new one. Tiering by size/complexity (not one blanket price) avoids under/over-pricing a tiny
café vs. a 5-location group.

### Verified market anchors (checked 2026-10-16)

**Foodics published pricing** (foodics.com/pricing, billed annually):
- Starter Bundle: 392/mo — basic POS, menu management, dashboards, KDS
- Basic Bundle: 742/mo — adds inventory, online ordering, accounting/HR
- Advanced Bundle: 1,133/mo — adds API integration, BI dashboards, loyalty
- Enterprise tier: quote-based, not published (sales-led, consistent with Oracle-tier positioning)

**Dubai restaurant revenue bands** (market research, cross-referenced):
- Small cafés/kiosks: AED 33,000–125,000/month
- Neighborhood restaurants: AED 50,000–220,000+/month
- Mid-range/standard restaurant benchmark: ~AED 300,000/month
- Food cost: ~28-32% of revenue · Labor: ~28% · Net margin: typically 3-10%, up to 12-20% well-run

### Proposed tiers

| Tier | Target restaurant | Monthly revenue band | Price/month |
|---|---|---|---|
| Starter | Single location, smaller menu (<20 items), simpler ops | ~100K-200K | 600-800 |
| Growth | Single location, standard casual dining (20-30 items) | ~200K-400K | 1,200-1,800 |
| Multi-location / Pro | 2-5 locations or high complexity (large menu, hotel F&B) | 400K+ | 2,500-4,000+ (custom) |

Positioned as an **affordable specialist add-on** on top of whatever POS the restaurant already
runs (Foodics, Oracle, or none) — Starter sits below Foodics' Advanced tier, Growth roughly
in-line, Pro above only where multi-location complexity genuinely justifies it. Not pitched as a
POS replacement or an undercut of Foodics — consistent with the "not competing with Oracle/
Foodics on day 1" positioning in Section 2.

### Metrics to gather BEFORE quoting (never quote blind)

Gathered via the POS health check (Section 5) — this is literally what that first engagement is
for:
1. **Monthly revenue** (or covers/month × average check if they won't share revenue directly) —
   determines the tier
2. **Number of active menu items requiring prep** (not full menu, just prepped dishes — matches
   PrepCast's actual scope) — complexity driver
3. **Number of locations/branches** — complexity driver
4. **Current food cost % and a rough waste estimate** (even gut-feel from the owner) — lets us
   calculate their specific potential savings, not just quote off a generic tier
5. **Current POS/system in use** (Foodics, Oracle, none) — determines integration effort and
   whether we're complementing or partially overlapping their existing spend

### Answering "what is your pricing based on?"

> "Our pricing is based on your restaurant's size and complexity — specifically your monthly
> covers, menu size, and number of locations — because that's what determines how much food-cost
> waste and stockout risk you actually have to recover. We priced it so that for a restaurant
> your size, the subscription costs a small fraction of what we expect to save you in reduced
> waste and fewer stockouts. We'll show you the real numbers from your own sales data in the
> pilot before you commit to anything — so you're not paying for a promise, you're paying for a
> result you've already seen on your own books."

Why this works: ties price to a tangible, restaurant-specific driver (owners already think this
way about their own costs); pre-emptively answers "is this worth it" by connecting price to
expected savings without promising a number before the pilot; offers proof before commitment,
removing the biggest objection a skeptical owner will raise.

### Pilot-to-paid commercial sequence

1. **Free health check** (Section 5) — low-commitment first touch, uses their own POS data
2. **Paid pilot at ~50% of tier price, 6-8 weeks**, with an agreed before/after comparison
   methodology (see Section 1 validation approach — same period last year, or a holdout split)
3. **Full tier price subscription** once savings are demonstrated on their own real data

This gives the owner a low-risk, proof-first path in, instead of asking for full commitment
before they've seen a result.

---

## Open questions / next decisions

- Which of these (health check, labor scheduling, ops bot) gets built first after the core
  PrepCast pilot — likely health check (near-zero build cost, immediate conversation starter)
- Who are the 2-3 friends being considered for the team, and what would their roles be
  (engineering vs. sales/ops vs. both)?
- What's the actual first pilot target — own workplace (Gastronomica, with permission) vs. a
  network contact elsewhere?
- Pricing model not yet decided: one-off project fee vs. monthly subscription vs. hybrid
  (small upfront + ongoing retainer) — worth deciding once there's a real pilot to anchor the
  conversation
