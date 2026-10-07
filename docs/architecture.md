# Architecture

This document covers the system design and technical decisions. Decisions are recorded as ADRs in [§13](#13-decision-log-adrs). If a decision changes, add a new ADR instead of rewriting the old one.

**Guiding rules**
1. **Copy the unified / Accounting Orbit stack (`C:\AI3\unified`).** When this app needs something unified already has (auth, sessions, lazy loading, account deletion, CI), copy that pattern or code instead of inventing a new one.
2. **Phone first.** Most people will use this on a phone. Every screen is designed for a phone and then stretched to fit desktop.
3. **Bare bones first.** Items tagged **[P1]** are needed for the first working version. **[P2]** items come right after. **[Later]** items are not scheduled yet. The roadmap follows the same tags.

---

## 1. What we're building

This is a campus-only app that shows every event on campus, so students always know what's going on, even if it's just people hanging out.

- **Calendar**: every event, arranged by time
- **Map**: every event, arranged by room
- **Favorites**: events from people you've favorited

A single **shared filter** drives both Calendar and Map.

### Web app first, then phone apps

| Step | What | Why |
|---|---|---|
| **[P1]** | **Installable web app (PWA)** | One codebase runs on iPhone, Android, and desktop. Students can "Add to Home Screen" and get an app icon and a full-screen app. There's no app store review and no fees |
| **[Later]** | iPhone + Android store apps via **Capacitor** | Capacitor wraps the *same* React build into native apps, so no rewrite is needed. We'd do this only if we need things the web can't do well |

Push notifications work in a PWA on Android, and on iPhone once the app is added to the home screen (iOS 16.4+). So `/alerts` can become push notifications later without a native app.

---

## 2. Tech stack (same as unified, kept small)

| Layer | Choice | Where it comes from in unified |
|---|---|---|
| Frontend | React (Vite, **JSX**) + MUI + TanStack Query | `ledger-ui/` |
| Routing | `wouter`, a ~2 KB router for real URLs like `/calendar` | new, because unified doesn't use URL routes |
| Lazy loading | Every page is `React.lazy()` with one `<Suspense>`, and vendor chunks are split in `vite.config.js` | `ledger-ui/src/app/views.js`, `vite.config.js` |
| PWA | `vite-plugin-pwa` (manifest + service worker + app icon) | new |
| Map rendering | SVG floor plans **[P1]**; 3D/video **[Later]** | new |
| Backend | FastAPI + SQLModel + Uvicorn (Python 3.12) | `ledger-core-pkg/backend/` |
| Migrations | Alembic | `backend/migrations/` |
| Database | **Neon** (serverless Postgres, free tier) in production; SQLite for local dev and tests | unified uses Supabase Postgres; Neon is the same Postgres without the weekly pause |
| Sign-in | **Sign in with Microsoft** (Entra ID, OpenID Connect) through `authlib`. No passwords stored | `routers/_auth_oauth.py` (same pattern as its Google sign-in) |
| 2FA | Handled by Microsoft (the college's own MFA) | — |
| Sessions | httpOnly cookie, revocable `AuthSession` row keyed by `jti`, CSRF on writes | `models/user.py`, `main.py` |
| Background jobs | `worker.py`: daily inactivity purge **[P2]** | `app/worker.py` |
| Errors | Sentry | same |
| Hosting | Vercel (frontend), Render (API only; no Render database), Neon (database) | `render.yaml` |
| CI | GitHub Actions | `.github/workflows/` |
| Tests | pytest (backend), Vitest (frontend), Playwright (e2e) | same |

What we're deliberately **not** adding: Redux or another state library (TanStack Query plus two contexts is enough), a CSS framework on top of MUI, a charting library, GraphQL, or websockets. The app polls for fresh events every 60 seconds while a tab is open, which is fine at campus scale.

---

## 3. Pages & URLs

| URL | Page | Who | Phase |
|---|---|---|---|
| `/` | Sign-in: one "Sign in with Microsoft" button. Signed-in users are redirected to `/home` | everyone | P1 |
| `/home` | **Happening now + next few hours**, plus the **+ New event** button | signed in | P1 |
| `/calendar` | All events by day/week/list, using the shared filter | signed in | P1 |
| `/map` | Campus → building → floor, with room badges, using the shared filter | signed in | P1 |
| `/favorites` | Events from people you favorited, plus your favorites list | signed in | P1 |
| `/hidden` | People and events you've hidden (archived), each with an **Unhide** button | signed in | P1 |
| `/alerts` | Your notices: "your event was cancelled by…" **[P1]**. Room-approval requests for SGA/owner and abuse flags for managers **[P2]** | signed in | P1/P2 |

Notes:
- The route is spelled `/calendar`.
- **No separate admin page in P1.** Tapping any person's name opens a small sheet with **Favorite · Hide**. Managers and the owner also see **Ban · Change role** there. The buttons shown come from the user's permission list.
- **Phone layout:** a bottom tab bar with **Home · Calendar · Map · Favorites · Alerts**. `/hidden` is reached from the profile menu.
- Vercel needs a rewrite rule (`vercel.json`) so that opening `/map` directly, or refreshing on it, loads the app.

### Lazy loading (copied from unified)

```js
// frontend/src/app/routes.js — same idea as unified's ledger-ui/src/app/views.js
import { lazy } from 'react';
export const ROUTES = {
  '/home':      lazy(() => import('../views/HomeView')),
  '/calendar':  lazy(() => import('../views/CalendarView')),
  '/map':       lazy(() => import('../views/MapView')),
  '/favorites': lazy(() => import('../views/FavoritesView')),
  '/hidden':    lazy(() => import('../views/HiddenView')),
  '/alerts':    lazy(() => import('../views/AlertsView')),
};
```

- Each page is its own chunk. The sign-in page downloads almost nothing, and nobody downloads the map code until they open `/map`.
- Floor-plan SVGs load per floor, only when that floor is opened.
- `manualChunks` splits `react`/`react-dom` and Sentry into their own vendor chunks, the same way unified does.
- **Size budget:** first load on a phone should stay under about 150 KB of gzipped JS. CI fails the build if it grows past that.

---

## 4. Repository structure

```
campus-events/
├── docs/
│   ├── roadmaps/roadmap.md
│   └── architecture.md
├── frontend/                      # React + Vite PWA (mirrors unified/ledger-ui)
│   ├── public/
│   │   ├── robots.txt             # Disallow: /   (private app)
│   │   ├── favicon.ico
│   │   ├── icons/                 # PWA home-screen icons
│   │   └── maps/                  # campus + floor-plan SVGs
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                # bottom tab bar + <Suspense> + router
│   │   ├── app/routes.js          # path → lazy page (see §3)
│   │   ├── api.js                 # fetch wrapper (credentials + CSRF)
│   │   ├── views/                 # HomeView, CalendarView, MapView, FavoritesView, HiddenView, AlertsView
│   │   ├── components/            # EventCard, EventForm, CancelDialog, PersonSheet, FilterBar…
│   │   ├── contexts/
│   │   │   ├── AuthContext.jsx    # current user + their permission list
│   │   │   └── FilterContext.jsx  # the ONE shared filter
│   │   ├── hooks/
│   │   └── __tests__/             # Vitest
│   ├── e2e/                       # Playwright (phone-sized viewport by default)
│   ├── vercel.json                # SPA rewrites
│   ├── vite.config.js
│   └── package.json
├── backend/                       # FastAPI (mirrors unified/ledger-core-pkg/backend)
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── permissions.py     # ← roles, permissions AND scheduling limits. THE file to edit.
│   │   │   ├── microsoft_auth.py  # token validation + tenant/domain gate
│   │   │   └── config.py          # reads .env
│   │   ├── routers/               # HTTP endpoints
│   │   ├── services/              # business logic; permission + scheduling checks happen here
│   │   │   ├── event_rules.py     # room limit, own-overlap, schedule-ahead, daily cap
│   │   │   └── recurrence.py      # expand a series into occurrences
│   │   ├── models/                # SQLModel tables
│   │   ├── schemas/               # request/response shapes (incl. EventFilter)
│   │   └── worker.py              # daily jobs
│   ├── migrations/                # Alembic
│   ├── tests/                     # pytest
│   ├── Dockerfile
│   └── requirements.txt
├── .github/workflows/
├── render.yaml
├── .env.example
├── .gitignore
└── README.md
```

Changes from your original layout: `controllers/` became `routers/` (the FastAPI name), tests sit next to their code, deploy config is `render.yaml` instead of `infrastructure/`, and local dev runs without Docker, since Docker doesn't start on this machine (see unified's `CLAUDE.md`).

---

## 5. Roles & permissions

### Roles (highest to lowest)

| Role | Who | Summary |
|---|---|---|
| `owner` | You | Can do anything to anyone. The only account allowed from any domain. Never auto-deleted |
| `manager` | Trusted staff/admins | Promote, demote, ban, cancel |
| `student_gov` | Student government (SGA) | Create events (up to 1 year ahead), cancel any event, approve room overlaps. **Cannot ban** |
| `security` | Campus security | Can view everything |
| `student` | Everyone else | Create events (up to 3 months ahead), favorite, hide |

### Permission matrix

| Permission | owner | manager | student_gov | security | student |
|---|:-:|:-:|:-:|:-:|:-:|
| View events | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create `friend_event` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create `club_event` | ✅ | ✅ | ✅ | ❌ | ✅ |
| Create `main_event` | ✅ | ✅ | ✅ | ❌ | ❌ |
| Edit/cancel **own** events | ✅ | ✅ | ✅ | ✅ | ✅ |
| Edit **any** event | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cancel **any** event | ✅ | ✅ | ✅ | ❌ | ❌ |
| Approve room overlap **[P2]** | ✅ | ❌ | ✅ | ❌ | ❌ |
| Ban / unban | ✅ | ✅ | ❌ | ❌ | ❌ |
| Promote / demote | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage buildings/rooms | ✅ | ✅ | ❌ | ❌ | ❌ |
| View moderation log **[P2]** | ✅ | ✅ | ❌ | ✅ | ❌ |
| Favorite / hide people | ✅ | ✅ | ✅ | ✅ | ✅ |

**Hierarchy rule:** you can only act on users below your own role, and you can only assign roles below your own. So only the owner can create managers.

### `backend/app/core/permissions.py`

This is the only file that decides access **and** scheduling limits. To change a rule, edit this file.

```python
from enum import Enum

class Role(str, Enum):
    OWNER = "owner"; MANAGER = "manager"; STUDENT_GOV = "student_gov"
    SECURITY = "security"; STUDENT = "student"

ROLE_RANK = {Role.OWNER: 100, Role.MANAGER: 80, Role.STUDENT_GOV: 60,
             Role.SECURITY: 40, Role.STUDENT: 20}

ALL = set(Role)
PERMISSIONS: dict[str, set[Role]] = {
    "event.view":            ALL,
    "event.create.friend":   ALL,
    "event.create.club":     ALL - {Role.SECURITY},
    "event.create.main":     {Role.OWNER, Role.MANAGER, Role.STUDENT_GOV},
    "event.edit_any":        {Role.OWNER},
    "event.cancel_any":      {Role.OWNER, Role.MANAGER, Role.STUDENT_GOV},
    "event.approve_overlap": {Role.OWNER, Role.STUDENT_GOV},
    "user.ban":              {Role.OWNER, Role.MANAGER},
    "user.change_role":      {Role.OWNER, Role.MANAGER},
    "map.manage":            {Role.OWNER, Role.MANAGER},
    "modlog.view":           {Role.OWNER, Role.MANAGER, Role.SECURITY},
}

# ── Scheduling limits ──
MAX_DAYS_AHEAD = {            # how far ahead you can schedule (single or recurring)
    Role.OWNER: 365, Role.MANAGER: 365, Role.STUDENT_GOV: 365,
    Role.SECURITY: 90, Role.STUDENT: 90,
}
CAN_DOUBLE_BOOK_SELF = {Role.OWNER, Role.MANAGER, Role.STUDENT_GOV}  # others: 1 event at a time
ROOM_MAX_OVERLAPPING = 2      # default; a Room can override it (e.g. the cafeteria)
MAX_EVENTS_CREATED_PER_DAY = {Role.STUDENT: 10, Role.SECURITY: 10}   # anti-spam; others unlimited

def can(role: Role, perm: str) -> bool: ...
def outranks(actor: Role, target: Role) -> bool: ...
```

**Enforcement:** the backend checks these on every write. `GET /auth/me` returns the user's role, permissions, and limits. The frontend uses that only to show or hide buttons and to grey out dates in the date picker. The frontend is never trusted.

---

## 6. Event rules

All of these live in `services/event_rules.py` and are checked on the server for every create or edit, including each occurrence of a recurring event.

| # | Rule | Phase |
|---|---|---|
| 1 | **Exactly one type per event:** `main_event`, `club_event`, or `friend_event`. It's a single required field | P1 |
| 2 | **Schedule-ahead limit:** an event, or the last occurrence of a series, can't be more than `MAX_DAYS_AHEAD[role]` from today. That's 3 months for regular users and 1 year for SGA, manager, and owner | P1 |
| 3 | **No double-booking yourself:** students and security can't have two of their own events that overlap in time. SGA, manager, and owner can | P1 |
| 4 | **Room limit:** at most `ROOM_MAX_OVERLAPPING` (2) events can overlap in the same room at the same time. **[P1]:** the 3rd event is blocked with "Room is full at that time". **[P2]:** instead of blocking, the 3rd event is saved as `pending_approval` and an alert goes to SGA and the owner, who can approve or reject it | P1 → P2 |
| 5 | **Daily creation cap** for students and security (anti-spam) | P1 |
| 6 | Events must end after they start, and are at most 12 hours long (a series repeats instead) | P1 |

**Abuse → ban.** **[P1]:** managers and the owner can ban from the person sheet. **[P2]:** a **Report** button on events, plus automatic flags to managers in `/alerts`, for example when someone hits the daily cap repeatedly, keeps getting blocked by the room limit, or gets reported several times. A human always makes the ban decision. Nothing bans anyone automatically.

---

## 7. Recurring events & cancelling

### Model

- A recurring event is an **EventSeries** (repeat rule + end date) plus one **Event row per occurrence**. We create all the occurrences up front, which is possible because the 3-month or 1-year limit keeps the number small.
- Storing each occurrence as a real row makes everything else simple. The calendar, the map, conflict checks, and cancelling a single date all work on ordinary `Event` rows.
- Repeat options **[P1]**: daily, weekly on chosen weekdays, every 2 weeks. The end date can't be later than the schedule-ahead limit.
- Every occurrence has to pass the rules in §6. If some dates conflict, the form lists them, and the user can **skip those dates** or change the time.

### Cancel buttons

Tapping a **one-off** event shows **Cancel event**.

Tapping an event that's **part of a series** shows two buttons:

```
[ Cancel event ]        → cancels only this date
[ Cancel recurring ]    → opens a choice:
                             ( ) Only this date
                             ( ) This and all future dates
                             ( ) The whole series (every date that hasn't happened yet)
                          [ Confirm ]
```

- Dates that have already happened are never changed.
- Cancelling sets `status = cancelled`. Cancelled events stay visible, crossed out, until their end time so nobody shows up for nothing. After that they disappear from views.
- The same dialog is used when SGA, a manager, or the owner cancels someone else's event. The creator gets a notice in `/alerts`.

---

## 8. Sign-in (Microsoft)

Both `@sunywcc.edu` (staff) and `@my.sunywcc.edu` (students) live in the same Microsoft tenant: **Westchester Community College**, tenant ID `4981a704-f6a3-4ac0-89c2-a3812354a3ff`. We confirmed this from Microsoft's public login metadata.

**Why:** we store no passwords, 2FA comes from the college's own MFA, it proves the account really belongs to the person, and accounts stop working when the college closes them. It's also the least login code possible: one button.

```
"Sign in with Microsoft"
   → Microsoft login (school MFA happens here)
   → /auth/microsoft/callback with ID token → validate signature, audience, issuer, expiry
   → tid == WCC tenant AND email is sunywcc.edu / *.sunywcc.edu   (or account == OWNER_EMAIL)
       no ──► "Only Westchester Community College accounts can use this app"
   → banned? ──► rejected
   → find user by (tid, oid) or create as `student` → session cookie → /home
```

Rules:
- Match the domain on a dot, so `my.sunywcc.edu` passes and `fakesunywcc.edu` doesn't.
- Identify users by `tid` + `oid`, never by email alone.
- `OWNER_EMAIL` may use any Microsoft account and is the only way to become owner.

**What we need from outside:** a free app registration in Microsoft Entra, which gives us the client ID, secret, and redirect URLs. We may also need **one-time consent from WCC IT** if students see "Need admin approval". We only ask for `openid profile email`. **Test this first (Milestone 1).**

**Plan B, if IT refuses:** our own login, using an email code to `@sunywcc.edu`/`@my.sunywcc.edu`, argon2-hashed passwords, and 2FA. That code already exists in unified (`_auth_password.py`, `_auth_mfa.py`).

**Security:** HTTPS everywhere, which Vercel and Render provide. No field-level encryption, since we store no passwords or sensitive data. **Banning** revokes all sessions, stores a hash of the Microsoft ID in `banned_accounts`, and cancels the user's upcoming events.

---

## 9. Inactivity purge (150 days) [P2]

- `last_active_at` updates on authenticated requests, at most once per hour.
- `worker.py` runs daily and **hard-deletes** users inactive for more than 150 days, except the owner. That removes the user, their sessions, their events and series, their favorites and hides, and other people's favorites or hides that point at them.
- Moderation-log entries stay, but show "deleted user".
- Bans survive, because the `tid:oid` hash in `banned_accounts` isn't deleted.
- The same code powers a **Delete my account** button.
- `INACTIVITY_DELETE_DAYS=150` is set in config.

This is P2 because nobody can hit 150 days of inactivity until 150 days after launch. `last_active_at` tracking starts in P1, though.

---

## 10. Data model

```
User
  id, ms_tenant_id, ms_object_id        -- unique together = identity
  email, display_name, role, is_banned, last_active_at, created_at

AuthSession            id, user_id, jti (unique), created_at, expires_at, revoked_at
BannedAccount          account_sha256 (pk) = sha256("tid:oid"), banned_at

Building               id, name
Floor                  id, building_id, level, floor_plan_svg
Room                   id, floor_id?, name, shape_ref, is_outdoor,
                       max_overlapping?        -- null = use ROOM_MAX_OVERLAPPING

EventSeries
  id, creator_id → User (cascade)
  freq: daily | weekly | biweekly, weekdays[], starts_on, ends_on
  -- title/type/room/time-of-day copied onto each occurrence

Event
  id, series_id? → EventSeries
  title, description
  type        : main_event | club_event | friend_event      -- exactly one
  room_id → Room
  starts_at, ends_at               -- UTC; displayed in America/New_York
  creator_id → User (cascade)
  status      : active | cancelled | pending_approval [P2] | rejected [P2]
  cancelled_by_id?, cancelled_reason?
  created_at, updated_at

UserFavorite           (user_id, favorite_user_id)
UserHidden             (user_id, hidden_user_id)            -- /hidden: hide a person
HiddenEvent            (user_id, event_id | series_id)      -- /hidden: hide one event or series

Alert                  id, user_id, kind, event_id?, message, read_at, created_at
                       -- kinds: event_cancelled [P1], approval_needed [P2], abuse_flag [P2]

Report [P2]            id, reporter_id, event_id, reason, created_at, resolved_by_id?
ModerationLog [P2]     id, actor_id?, action, target_user_id?, target_event_id?, reason, created_at
```

**Feed rule:** show `active` events (and `cancelled` ones until they end), except events from people you've hidden and events you've hidden. The Favorites page shows only events from people you've favorited.

---

## 11. The shared filter & the map

**Filter:** there is one filter, held in `FilterContext.jsx` and mirrored to the URL query string, so switching between `/calendar` and `/map` keeps it. On a phone it's a single **Filter** button that opens a bottom sheet.

```python
class EventFilter(BaseModel):
    types: list[EventType] = list(EventType)
    start: datetime | None = None        # default: now
    end: datetime | None = None          # default: end of today
    happening_now: bool = False
    building_ids: list[int] = []
    room_ids: list[int] = []
    favorites_only: bool = False
    search: str = ""
```

`GET /events?<filter>` is used by both views. They share one TanStack Query cache, so switching tabs doesn't refetch.

**Map [P1]:** record each building, floor, room, and outdoor spot, then draw each floor as an SVG whose room shapes have IDs matching `Room.shape_ref`. Rooms get a badge showing their event count under the current filter. The design supports tap targets and pinch-zoom on phones.

**Map [Later]:** an immersive campus video or 360° layer, linked to the same room IDs.

---

## 12. Configuration (`.env.example`)

```
DATABASE_URL=sqlite:///./dev.db          # production: Neon connection string (postgresql://…?sslmode=require)
MS_CLIENT_ID=
MS_CLIENT_SECRET=
MS_REDIRECT_URI=http://localhost:8000/auth/microsoft/callback
ALLOWED_TENANT_IDS=4981a704-f6a3-4ac0-89c2-a3812354a3ff   # Westchester Community College
EMAIL_DOMAIN_REQUIREMENT=sunywcc.edu                      # subdomains allowed
OWNER_EMAIL=
SESSION_SECRET=
INACTIVITY_DELETE_DAYS=150
FRONTEND_ORIGIN=http://localhost:5173
SENTRY_DSN=
```

Scheduling limits are **not** env vars. They live in `permissions.py` (§5), so all the rules are in one place.

---

## 13. Decision log (ADRs)

| # | Decision | Status |
|---|---|---|
| ADR-001 | Copy the unified stack: React/Vite/MUI + FastAPI/SQLModel/Postgres, Vercel + Render | Accepted (database changed by ADR-015) |
| ADR-002 | Roles, permissions, and scheduling limits live in one file (`core/permissions.py`); the frontend reads them from `/auth/me` | Accepted |
| ADR-003 | Access gate: WCC Microsoft tenant plus the `sunywcc.edu` / `*.sunywcc.edu` domain, matched on a dot. Owner exempt | Accepted |
| ADR-004 | Sign in with Microsoft; 2FA delegated to the college; no passwords. Plan B is our own login from unified's code | Accepted |
| ADR-005 | No field-level encryption; HTTPS everywhere | Accepted |
| ADR-006 | Hard-delete after 150 days inactive (owner exempt); bans persist as hashes | Accepted |
| ADR-007 | One shared filter, synced to the URL, used by Calendar and Map | Accepted |
| ADR-008 | SVG floor-plan map first; video/3D later | Accepted |
| ADR-009 | Cancel is a soft state, not a delete | Accepted |
| ADR-010 | Local dev without Docker | Accepted |
| ADR-011 | **Web app (PWA) first**; native iPhone/Android later by wrapping the same build with Capacitor | Accepted |
| ADR-012 | Real URL routes (`/home`, `/calendar`, `/map`, `/favorites`, `/hidden`, `/alerts`) with `wouter`; every page lazy-loaded as in unified; JS size budget enforced in CI | Accepted |
| ADR-013 | Recurring events are stored as one row per occurrence (`EventSeries` + `Event`), made possible by the 3-month/1-year limit | Accepted |
| ADR-014 | Room limit of 2 overlapping events: blocked in P1, approval flow to SGA/owner in P2 | Accepted |
| ADR-015 | Production database is **Neon** free-tier Postgres, not Render Postgres or SQLite-on-disk. Reasons: free with no expiry, scales to zero when idle and wakes in under a second, managed backups, and no disk on the API server. App data can't live in users' Microsoft accounts, because events must be shared and checked centrally (room limits, bans) | Accepted |
| ADR-016 | Dependency versions match unified (React 19, MUI 5, TanStack Query 5, Vite 8, Vitest 4, oxlint; FastAPI 0.139, SQLModel 0.0.39, Alembic 1.18) so its code copies over unchanged. MUI icons are imported per icon from `@mui/icons-material/esm/<Name>`: the barrel made tests ~30× slower and the CommonJS deep path breaks in Vite dev | Accepted |
| ADR-017 | The service worker precaches only the app shell and icons. Page chunks are cached the first time they're opened, so the service worker never pulls `/map` code in the background (keeps ADR-012's lazy loading true after install) | Accepted |
| ADR-018 | Sessions use an opaque random token in the httpOnly cookie (not a JWT); `AuthSession.jti` stores only its SHA-256. Sessions last 30 days and are revocable (logout, ban). No JWT library needed, and a database leak yields no usable sessions | Accepted |
| ADR-019 | CSRF is unified's double-submit check (fails closed, Origin must be `FRONTEND_ORIGIN`). `GET /auth/me` also returns the token in its body, because on a cross-site deploy the page can't read the API's cookie | Accepted |
| ADR-020 | `User.role` is stored as a plain string (a `Role` value), not a database enum, so adding a role is a `permissions.py` edit with no migration | Accepted |
| ADR-021 | The backend uses the `tzdata` package (IANA time zones) so recurring events keep their New York wall-clock time across daylight saving on every OS, including Windows. Phones and browsers use their built-in `Intl` data; no date library on the frontend | Accepted |
| ADR-022 | **One migration until launch.** `migrations/versions/0001_initial_schema.py` is regenerated whenever models change, and local `dev.db` is reset (`alembic upgrade head` + `python -m app.seed`). From launch on, every schema change gets its own migration | Accepted |
| ADR-023 | Local developer sign-in ("sign in as" an email + role, no password) for testing before and alongside Microsoft. Only when `DEV_LOGIN=1` **and** `FRONTEND_ORIGIN` is `http://localhost…`; any HTTPS deploy refuses it. Still gated to WCC domains. Does not change ADR-004: real users never have passwords | Accepted |
| ADR-024 | Event details: Home's "next few hours" is 4 hours; the daily cap counts one-off events plus series (a repeat counts once) created in the last 24 hours; repeats are expanded on the server into rows at the same New York time; edits are per occurrence | Accepted |
| ADR-025 | **Favorites** has two parts: ★ `SavedEvent` (one occurrence, or a whole `series_id`) and ♥ `UserFavorite` (follow a person: all their upcoming events). Every event response carries the viewer's `saved` state. Pulled forward from Milestone 4 at the owner's request | Accepted |
| ADR-026 | **Add to calendar** is generated in the browser with no library: a standard `.ics` file (Apple Calendar, Outlook, Samsung/Android calendar apps, Linux) and a Google Calendar template link. Times are UTC in the file, so every device shows its own local time | Accepted |
| ADR-027 | CSRF exemptions (refines ADR-019, same idea as unified's list): sign-in routes (`/auth/dev-login`, `/auth/microsoft/…`) and logout from the app's own Origin. A stale or expired session cookie must never stop someone from signing in again | Accepted |
| ADR-028 | **Recommended** = `main_event`s **or** events tagged with your major. People pick one major (profile menu); creators may tag an event with up to 3 majors. The majors live in one file, `backend/app/core/majors.py` (like `permissions.py`), stored as stable keys; event tags are stored `",key1,key2,"` so matching is exact. The starter list is a placeholder until WCC's program list is in | Accepted |
| ADR-029 | **Microsoft sign-in details.** The `common` endpoint (so the owner may use a personal Microsoft account); state + nonce + PKCE kept in a 10-minute HMAC-signed cookie (`SESSION_SECRET`), no server-side session store; ID token checked with joserfc (already a dependency of authlib) against Microsoft's published keys, with audience, `iss == https://login.microsoftonline.com/{tid}/v2.0`, expiry and nonce. Email = `email` or `preferred_username`. **Narrows ADR-003:** `OWNER_EMAIL` is honoured only from the WCC tenant or Microsoft's personal-account tenant (`9188040d-…`), because any other tenant's admin can put any email on an account | Accepted |
| ADR-030 | **Sentry is opt-in and private.** Backend `sentry-sdk` and frontend `@sentry/react` start only when `SENTRY_DSN` / `VITE_SENTRY_DSN` are set, with `send_default_pii=False` (no IPs, cookies or request bodies). The frontend loads Sentry with a dynamic import, so it never counts against the first-load budget (when unset, the bundler drops it entirely) | Accepted |
| ADR-031 | **Phase 2 mechanics.** (a) Room approval: only a full room becomes `pending_approval`; other rule breaks are still conflicts; pending events don't count toward room limits; one `approval_needed` alert per request to everyone with `event.approve_overlap`; approving/rejecting applies to the series' pending dates. (b) Abuse flags alert everyone with `user.ban`, once when a threshold is reached; thresholds live in `permissions.py`. (c) The daily purge runs as a background task inside the API (no paid cron); `WORKER_ENABLED=0` turns it off. (d) Deletion is explicit row-by-row (not DB cascades) so SQLite and Postgres behave the same. (e) Offline = Workbox `NetworkFirst` cache of API reads, per device, deleted at sign-out | Accepted |
| ADR-032 | **Where + majors.** Every event has `location_kind`: `campus` (a `Room`; room limits and the map apply), `off_campus` (free-text place/address) or `online` (an http(s) link, checked on the server and linked with `rel=noopener`). Self double-booking applies to all kinds. Majors live in `backend/majors.txt`, one per line, re-read when the file changes (no restart); the key is a slug of the line, so renaming orphans the old key and those people are asked again. New users are asked for a major right after the terms. Starting list: WCC's 44 degree programs from the Fall 2026 – Summer 2027 catalog. Extends ADR-028 | Accepted |
| ADR-033 | **Fast and slick.** (a) Instant taps: Save, Hide and Cancel update every cached list at once (TanStack `onMutate`) and roll back if the server refuses (`lib/optimistic.js`). (b) Skeleton cards instead of spinners. (c) Tab code is fetched when the phone is idle and the moment a finger touches a tab; the map image too. (d) Dark mode follows the system setting. (e) An install hint: iPhone (Share → Add to Home Screen, since iOS never prompts) and Android/desktop (the browser's install prompt), dismissible for 30 days. (f) The map's fitted size is pure CSS (container units), so it re-fits on resize/rotation; needs iOS Safari 16+ / Chrome 105+. (g) App name, colours and icon live in `frontend/brand/` and regenerate every icon size with one script. (h) API responses are gzip-compressed and list endpoints use a constant number of queries | Accepted |

---

## 14. Open questions

1. **Will WCC IT allow the Microsoft sign-in app?** Test this first. If IT says no, use Plan B (§8).
2. **Does the college approve of this?** It uses the school name and school accounts, and shows where students are in real time. You can ask about this together with item 1.
3. **Room limit reading:** I read your rule as "2 events can share a room; the 3rd needs approval". If you meant "any 2 events overlapping needs approval", change `ROOM_MAX_OVERLAPPING` to 1.
4. **Big shared spaces** like the cafeteria and the quad will hit a limit of 2 quickly, especially with `friend_event`s. Set a higher `max_overlapping` on those rooms?
5. **Location privacy** for `friend_event`s, and **under-18** dual-enrollment students (see item 2).
6. **Terms of use / privacy note** at first sign-in **[P2]**.
7. **Floor plans:** trace existing campus maps, or draw them from scratch?
