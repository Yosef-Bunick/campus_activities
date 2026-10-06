# Roadmap

Goal: **students always know what's going on around campus, even if it's just people hanging out.**

**Priority:** bare bones first (**Phase 1**), then the smaller rules and polish (**Phase 2**), then everything else (**Later**). We copy the **unified / Accounting Orbit** stack and reuse its code wherever it fits.

We're building an **installable web app (PWA)** that works on iPhone, Android, and desktop from one codebase, and designing it **phone first**. Native store apps come later by wrapping the same build.

Status legend: ⬜ not started · 🟨 in progress · ✅ done

---

# Phase 1: Bare bones

## Milestone 0: Foundation 🟨
- [x] Folder structure from [architecture.md §4](architecture.md#4-repository-structure) (Dockerfile, `render.yaml`, `worker.py`, `e2e/` deferred, see Milestone 4 and Phase 2)
- [x] Backend: FastAPI + SQLModel + Alembic, scaffolded from unified's `ledger-core-pkg/backend` (`/health` checks the DB; empty baseline migration `0001`)
- [x] Frontend: React + Vite + MUI + TanStack Query, scaffolded from unified's `ledger-ui`
- [x] Routes `/`, `/home`, `/calendar`, `/map`, `/favorites`, `/hidden`, `/alerts`, **each lazy-loaded** (unified's `views.js` pattern) with `wouter`
- [x] Phone layout: bottom tab bar (Home · Calendar · Map · Favorites · Alerts); `/hidden` in the profile menu
- [x] PWA: manifest, icons, service worker, so it can be added to the home screen (icons are placeholders until the app has a name)
- [x] `vercel.json` rewrites so deep links like `/map` work
- [x] `.env.example`, `.gitignore`, `robots.txt` (disallow all)
- [x] Local dev without Docker (SQLite + `uvicorn` + `npm run dev`)
- [x] CI: pytest + ruff, Vitest + lint, and a **JS size budget** (~150 KB gzipped on first load). First-load JS is 124 KB today
- [x] Push to GitHub and see both workflows go green ([Yosef-Bunick/campus_activities](https://github.com/Yosef-Bunick/campus_activities), 2026-10-06)
- [ ] Add to the home screen on a real phone (needs HTTPS, so this happens with the first deploy)

**Done when:** the app opens on a phone, can be added to the home screen, every tab loads its own chunk, and CI is green.

## Milestone 1: Sign-in and roles 🟨
- [ ] **First step:** register the app in Microsoft Entra and test with a real `@my.sunywcc.edu` account. If you see "Need admin approval", contact WCC IT. If IT blocks it, switch to Plan B (architecture §8). *Waiting on the Entra keys; everything below that doesn't need Microsoft was built first (2026-10-06)*
- [x] Local developer sign-in for testing without Microsoft (`DEV_LOGIN=1`, localhost only; ADR-023)
- [x] "Sign in with Microsoft", a single button: `/auth/microsoft/login` + `/callback` with state, nonce and PKCE; the ID token's signature, audience, issuer, expiry and nonce are checked (joserfc, shipped with authlib), then `services/accounts.sign_in()`. Tested end to end against a fake Microsoft. The button turns on by itself once the keys are in `.env` (ADR-029)
- [x] Owner exemption only trusted from the WCC tenant or Microsoft's personal-account tenant, so another tenant can't claim `OWNER_EMAIL` (ADR-029)
- [x] Gate: WCC tenant **and** `sunywcc.edu` / `*.sunywcc.edu`; `OWNER_EMAIL` is exempt and becomes owner (`services/accounts.py`, tested with fake identities)
- [x] Revocable sessions (httpOnly cookie + CSRF), copied from unified (ADR-018, ADR-019)
- [x] Roles + **`backend/app/core/permissions.py`**: permissions **and** scheduling limits in one file
- [x] `/auth/me` returns role, permissions, and limits; `AuthContext.jsx`; signed-out people only reach `/`, signed-in people skip it
- [x] Person sheet (tap a name): Favorite · Hide, plus Ban · Change role for managers/owner, following the hierarchy rule. *Favorite/Hide buttons are shown but disabled until Milestone 4 stores them; the sheet gets opened from names once events exist (Milestone 2)*
- [x] Ban revokes sessions and blocks the account through the banned hash. *Cancelling upcoming events moves to Milestone 2*
- [x] `last_active_at` tracking (at most once an hour)

**Done when:** WCC accounts can sign in, everyone else is rejected (except the owner), and editing `permissions.py` changes what people can do.

## Milestone 2: Events, Home and Calendar 🟨
- [x] Create, edit, and cancel events. Each event has **exactly one type**: `main_event`, `club_event`, or `friend_event`
- [x] Rules enforced on the server (architecture §6), all limits from `permissions.py`:
  - [x] schedule at most **3 months ahead** (students/security) or **1 year** (SGA, manager, owner)
  - [x] students/security can't have **two of their own events at the same time**
  - [x] **room limit:** max 2 overlapping events per room, and a 3rd is **blocked** for now
  - [x] daily creation cap (anti-spam): one-offs + series created in the last 24 hours (ADR-024)
- [x] **Recurring events:** daily / weekly on chosen days / every 2 weeks, within the schedule-ahead limit. Conflicting dates are listed and can be skipped
- [x] **Cancel buttons:** "Cancel event" (this date) and "Cancel recurring" with a choice of *only this date / this and future / whole series*
- [x] Cancelled events stay visible, crossed out, until they end. The creator gets a notice in `/alerts` (stored now; the page is Milestone 4)
- [x] Banning someone cancels their upcoming events
- [x] Tapping a creator's name opens the person sheet
- [x] Rooms: the 4 test rooms from `pin-map.html` (38, 26, 25D on floor 1; 108 on floor 2) in a placeholder "Test building", seeded by `python -m app.seed`
- [x] **`/home`**: happening now + next 4 hours, plus a **+ New event** button
- [x] Home **time chips** (Now · Next 4h · Today · This week) and a **Recommended** chip: main events + events tagged for your major (ADR-028). Pick your major in the profile menu; tag up to 3 majors on an event
- [ ] Replace the placeholder majors in `backend/app/core/majors.py` with WCC's real program list
- [x] **`/calendar`**: day / week / list
- [x] **Shared filter** (bottom sheet on phones), synced to the URL and shared by Calendar and Map
- [x] Times stored in UTC and shown in New York time (`tzdata` on the server, the browser's `Intl` on phones; ADR-021)
- [ ] You try it on your phone-size screen and say it feels right
- [x] **Add to calendar** on every event: `.ics` (Apple, Outlook, Samsung, Linux) and a Google Calendar link (ADR-026)

**Done when:** a student can post "studying in 204, 3 to 5pm, every Tuesday" from their phone, and everyone sees it.

## Milestone 3: Map 🟨
- [ ] Mapping pass: every building, floor, room, and outdoor spot gets an ID. *4 test rooms so far in **TEC** (38, 26, 25D on floor 1; 108 on floor 2), pinned on `WCC_MAP2.png`. Needs the full room list*
- [x] Campus map (`WCC_MAP2.png` as a 73 KB WebP, loaded only on `/map`) with room pins, pinch-zoom and +/− buttons
- [ ] SVG floor plans (lazy-loaded per floor) with tappable rooms. *Waiting for the real plans from facilities (2026-10-06 decision); the campus-map pins work until then*
- [x] **`/map`**: rooms badged with their event count (Now / Today), using the same shared filter
- [x] Tap a room to see its events

**Done when:** you can open the map on your phone and see which rooms have something going on right now.

## Milestone 4: Favorites, Hidden, Alerts 🟨
- [x] **`/favorites`**: ★ saved events (one date or a whole series) and events from people you favorite (♥ in the person sheet). Pulled forward at your request (ADR-025)
- [x] **`/hidden`**: people and events/series you've hidden, with Unhide. Hide from an event card (this date / all dates) or the person sheet; hidden things drop out of every feed
- [x] Person sheet **Favorite** button (`UserFavorite`)
- [x] Person sheet **Hide** button (`UserHidden`)
- [x] **`/alerts`**: "your event was cancelled" notices, with a read/unread state, Mark all read, and an unread badge on the Alerts tab
- [ ] Deploy (Vercel frontend + Render API + **Neon** database), turn on Sentry, and **pilot with a small group**
  - [x] `render.yaml` (API only) + Postgres driver (`psycopg2-binary`, as unified) in `requirements.txt`; run `alembic upgrade head` on start
  - [x] CI builds, checks, tears down and rebuilds the migration on real Postgres 16, seeds it, and boots the API against it
  - [ ] Set `VITE_API_BASE` in Vercel; add the Vercel URL to `FRONTEND_ORIGIN`
  - [ ] Make the session cookie first-party: iPhone Safari blocks cookies from a different site, so `*.vercel.app` → `*.onrender.com` won't keep anyone signed in. Needs the domain decision (`app.` + `api.` on one domain, or a Vercel `/api` rewrite)
  - [ ] Real app icons and name in the PWA manifest
  - [x] Playwright smoke test at phone size (`frontend/e2e/`): sign in → post → Calendar → save → Favorites → Map, no sideways overflow. Runs in CI (`e2e.yml`); locally `npm run e2e` (set `PW_CHANNEL=chrome` to reuse installed Chrome)
  - [x] Sentry wired, off until `SENTRY_DSN` / `VITE_SENTRY_DSN` are set (ADR-030)

**Done when:** the pilot group uses it on their phones for a week.

---

# Phase 2: Rules & polish (after the pilot)

- [ ] **Room approval flow:** a 3rd overlapping event becomes `pending_approval`, an alert goes to **SGA and the owner** in `/alerts`, and they approve or reject it
- [ ] Per-room overlap limit (cafeteria, quad, and similar spaces)
- [ ] **Abuse handling:** Report button; auto-flags to managers (repeated cap hits, repeated room blocks, multiple reports) → a human decides whether to ban
- [ ] Moderation log (owner, manager, security)
- [ ] **150-day inactivity purge** (daily job; owner exempt; bans persist) + **Delete my account**
- [ ] Short terms of use / privacy note at first sign-in
- [ ] "Extend series" button when a recurring event nears its 3-month or 1-year end
- [ ] Offline: show the last-loaded events when there's no signal

---

# Later (not scheduled)
- Follow a **club** (not just a person) once clubs exist as entities
- Calendar **subscription feed** (webcal) of your saved events, so new ones appear automatically
- **Native iPhone + Android apps**, by wrapping the same React build with Capacitor
- **Push notifications** (PWA push works on Android, and on iPhone once added to the home screen)
- **Immersive map:** full campus video / 360° / 3D linked to the same rooms
- Clubs as real entities, with club officers posting `club_event`s
- RSVPs and "I'm here" check-ins
- "Hide my name" on `friend_event`s
- Analytics for managers (busy rooms, busy times)
- Pull in more shared pieces from **accounting orbit** where it saves time

## Open questions
Tracked in [architecture.md § Open questions](architecture.md#14-open-questions).
