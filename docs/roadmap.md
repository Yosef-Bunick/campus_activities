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
- [ ] Push to GitHub and see both workflows go green (needs a GitHub repo)
- [ ] Add to the home screen on a real phone (needs HTTPS, so this happens with the first deploy)

**Done when:** the app opens on a phone, can be added to the home screen, every tab loads its own chunk, and CI is green.

## Milestone 1: Sign-in and roles ⬜
- [ ] **First step:** register the app in Microsoft Entra and test with a real `@my.sunywcc.edu` account. If you see "Need admin approval", contact WCC IT. If IT blocks it, switch to Plan B (architecture §8)
- [ ] "Sign in with Microsoft", a single button (OIDC via `authlib`, unified's Google sign-in pattern)
- [ ] Gate: WCC tenant **and** `sunywcc.edu` / `*.sunywcc.edu`; `OWNER_EMAIL` is exempt and becomes owner
- [ ] Revocable sessions (httpOnly cookie + CSRF), copied from unified
- [ ] Roles + **`backend/app/core/permissions.py`**: permissions **and** scheduling limits in one file
- [ ] `/auth/me` returns role, permissions, and limits
- [ ] Person sheet (tap a name): Favorite · Hide, plus Ban · Change role for managers/owner, following the hierarchy rule
- [ ] Ban revokes sessions, blocks the account through the banned hash, and cancels upcoming events
- [ ] `last_active_at` tracking

**Done when:** WCC accounts can sign in, everyone else is rejected (except the owner), and editing `permissions.py` changes what people can do.

## Milestone 2: Events, Home and Calendar ⬜
- [ ] Create, edit, and cancel events. Each event has **exactly one type**: `main_event`, `club_event`, or `friend_event`
- [ ] Rules enforced on the server (architecture §6):
  - [ ] schedule at most **3 months ahead** (students/security) or **1 year** (SGA, manager, owner)
  - [ ] students/security can't have **two of their own events at the same time**
  - [ ] **room limit:** max 2 overlapping events per room, and a 3rd is **blocked** for now
  - [ ] daily creation cap (anti-spam)
- [ ] **Recurring events:** daily / weekly on chosen days / every 2 weeks, within the schedule-ahead limit. Conflicting dates are listed and can be skipped
- [ ] **Cancel buttons:** "Cancel event" (this date) and "Cancel recurring" with a choice of *only this date / this and future / whole series*
- [ ] Cancelled events stay visible, crossed out, until they end. The creator gets a notice in `/alerts`
- [ ] **`/home`**: happening now + next few hours, plus a **+ New event** button
- [ ] **`/calendar`**: day / week / list
- [ ] **Shared filter** (bottom sheet on phones), synced to the URL and shared by Calendar and Map
- [ ] Times stored in UTC and shown in New York time

**Done when:** a student can post "studying in 204, 3 to 5pm, every Tuesday" from their phone, and everyone sees it.

## Milestone 3: Map ⬜
- [ ] Mapping pass: every building, floor, room, and outdoor spot gets an ID
- [ ] SVG floor plans (lazy-loaded per floor) with tappable rooms and pinch-zoom
- [ ] **`/map`**: rooms badged with their events, using the same shared filter
- [ ] Tap a room to see its events

**Done when:** you can open the map on your phone and see which rooms have something going on right now.

## Milestone 4: Favorites, Hidden, Alerts ⬜
- [ ] **`/favorites`**: events from people you favorited
- [ ] **`/hidden`**: people and events/series you've hidden, with Unhide
- [ ] **`/alerts`**: "your event was cancelled" notices, with a read/unread state
- [ ] Deploy (Vercel frontend + Render API + **Neon** database), turn on Sentry, and **pilot with a small group**
  - [ ] `render.yaml` (API only) + Postgres driver (`psycopg2-binary`, as unified) in `requirements.txt`; run `alembic upgrade head` on start
  - [ ] Set `VITE_API_BASE` in Vercel; add the Vercel URL to `FRONTEND_ORIGIN`
  - [ ] Real app icons and name in the PWA manifest
  - [ ] Playwright smoke test at phone size (`frontend/e2e/`)

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
