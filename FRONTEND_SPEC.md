# Frontend Contract — Spend Guardian Dashboard

This is a contract, same as `agents/*.md`. Read fully before writing any
frontend code. Do not deviate without explicit instruction.

## Role

A thin, read-only display layer over the existing API. It shows what the
pipeline already produced and lets a human approve a draft. It contains
**zero business logic** — no duplicate waste-detection rules, no
confidence calculations, no cost math. Every number and judgment shown on
screen comes directly from an API response, verbatim.

## Why this matters

The entire safety design of this project rests on the agent pipeline
being the only place decisions get made, with a human approval gate
before any external action. If the frontend starts recomputing or
re-deciding anything client-side, that guarantee is no longer actually
true — it just looks true. The UI's only job is to render API responses
and call the approve endpoint. Nothing else.

## Tech stack

React + Vite. Plain CSS or Tailwind utility classes — no additional state
management library (no Redux/Zustand/etc.), this app is too simple to
need one. `fetch` or `axios` for API calls, nothing more elaborate.

## Allowed API calls — this is the complete list, no others

- `GET /flags` — list all WasteFlags from the last audit run
- `GET /drafts` — list all ActionDrafts
- `POST /draft` — trigger the Action agent for a selected flag
- `POST /approve` — approve a draft (moves it to SENT via Slack)

If a feature seems to need an endpoint that doesn't exist yet, stop and
ask — don't invent a new backend route inside a frontend-focused session.

## Pages / views (this is the complete scope)

Three tabs: **Dashboard** (default) | **Flags** | **Drafts**.

1. **Dashboard view** — bento grid landing page. Visual style: white
   background (#FFFFFF), cards in #F9FAFB with #EFF6FF accent cards,
   16px border-radius, subtle hover scale, Inter/system font, blue
   (#3B82F6) to purple (#8B5CF6) gradient on the highlight stat card.
   3-column responsive grid, mixed card sizes (one large 2x2, one tall
   1x2 gradient stat card, four small 1x1 cards). All values computed
   from existing API responses (see "Allowed display aggregation"
   below) — no new endpoints.
2. **Flags view** — table or card list of WasteFlags: vendor, category,
   confidence, monthly cost, reason, requires_human_review (always shown
   as true). Read-only.
3. **Drafts view** — list of ActionDrafts with status (DRAFTED /
   APPROVED / SENT), recipient, subject, body preview. One **Approve**
   button per drafted item, calling `POST /approve`.
4. That's it. No search inputs, no filter controls exposed to the user,
   no charts, no auth, no settings pages. These add surface area with
   zero scoring benefit for a hackathon demo.

## Allowed display aggregation (not "business logic")

The Dashboard view is allowed to compute simple display aggregates from
existing API responses — this is presentation math, not a new decision,
and is fine:
- Sum of `monthly_cost` across all flags → "Total Savings" stat.
- `flags.length` → flag count.
- `drafts.filter(d => d.status === 'DRAFTED').length` → pending count.
- Unique vendor names from `flags` → "Top vendors" list.
- `new Date()` at the moment the dashboard fetches data → "Last
  refreshed" timestamp. Do NOT read `runs/last_audit.json` directly —
  that's a server-side file the frontend has no route to, and adding one
  would violate the no-new-endpoints rule. A client-side fetch timestamp
  is an honest substitute, just label it "Last refreshed," not "Last
  audit run."

What's still forbidden: anything that re-derives a *judgment* the
backend already made — re-scoring confidence, re-deciding what counts as
a duplicate, recalculating `monthly_cost` per flag instead of just
summing the existing values. If it's arithmetic over already-decided
values, it's fine. If it's a new decision, it's not.

## Guardrails — non-negotiable

- No business logic. If you find yourself writing an `if` statement that
  decides whether something is "duplicate" or "waste" or computes a
  dollar total, stop — that belongs in `waste_detection.py` or
  `recommendation.py`, not here.
- No new backend endpoints invented to make a UI feature easier — work
  within the four calls listed above.
- No optimistic UI that shows a draft as "SENT" before the API confirms
  it — wait for the real response, since the whole point of the approval
  gate is that nothing happens until a human explicitly confirms it.
- Display `requires_human_review` and `confidence_score` exactly as
  returned — don't reformat MEDIUM into something that reads as more or
  less certain than the backend actually says.

## The one allowed backend touch

`api/main.py` needs CORS middleware enabled so a Vite dev server (a
different origin) can call it. This is the only backend file this session
is allowed to modify, and only to add CORS — no other change to
`api/main.py` is in scope here.

## File structure

```
frontend/
├── src/
│   ├── App.jsx               # tab state: 'dashboard' | 'flags' | 'drafts'
│   ├── components/
│   │   ├── TabNav.jsx
│   │   ├── DashboardView.jsx # bento grid, default tab
│   │   ├── FlagsView.jsx
│   │   └── DraftsView.jsx
│   ├── api/client.js       # the only file allowed to call fetch() / the 4 endpoints above
│   └── main.jsx
├── index.html
├── package.json
└── vite.config.js
```

## Known failure mode to watch for

A coding agent given loose rein on a "dashboard" task will often add
scope on its own initiative — extra endpoints, mock data fallbacks that
hide real API failures, client-side recalculation "for responsiveness."
Watch for this specifically and reject it the same way unrequested
changes to `data/` got caught and reverted earlier in this build.