# Campus Events (working name)

A campus-only app that shows **what's happening on campus right now**, from official events to club meetings to a few friends hanging out in a room.

It's a **phone-first web app** that works on iPhone, Android, and desktop and can be added to your home screen like a regular app. Native store apps may come later.

## Pages

| URL | What it shows |
|---|---|
| `/home` | What's happening now and in the next few hours, plus **+ New event** |
| `/calendar` | Every event on campus, by day, week, or list |
| `/map` | The same events, placed on the campus map by room |
| `/favorites` | Events from people you've favorited |
| `/hidden` | People and events you've hidden |
| `/alerts` | Notices, such as "your event was cancelled" |

One **shared filter** controls both Calendar and Map.

## Who can sign in

- **Sign in with Microsoft.** Only Westchester Community College accounts (`@sunywcc.edu` and `@my.sunywcc.edu`) are allowed. 2FA comes from the college's Microsoft login, and we store no passwords.
- The **Owner** is the only exception and can use any Microsoft account.
- Accounts inactive for **150 days** are deleted automatically (except the owner).
- Roles: **Owner → Manager → Student Government → Security → Student**. All roles, permissions, and scheduling limits live in one file: `backend/app/core/permissions.py`.

## Events

- Each event has exactly one type:
  - `main_event`: official or campus-wide events
  - `club_event`: events run by a club
  - `friend_event`: informal meetups ("we're in room 204 studying")
- You can schedule up to **3 months** ahead, or **1 year** for Student Government and above. Events can repeat.
- Students can't have two of their own events at the same time.
- A room can hold at most 2 overlapping events. A 3rd will need approval from SGA or the owner.

Full rules are in [docs/architecture.md](docs/architecture.md#6-event-rules).

## Stack

The same stack as unified / Accounting Orbit: **React (Vite + MUI)**, installable as a PWA, with lazy-loaded pages; **FastAPI + SQLModel**; **PostgreSQL on Neon** (free tier). The frontend runs on Vercel and the API on Render.

## Docs

- [docs/roadmaps/roadmap.md](docs/roadmaps/roadmap.md): Phase 1 (bare bones), Phase 2 (rules & polish), and Later
- [docs/architecture.md](docs/architecture.md): design, pages, rules, data model, and decisions (ADRs)

## Repo layout (planned)

```
docs/            roadmap + architecture
frontend/        React PWA (pages, components, tests)
backend/         FastAPI: routers, services, models, permissions.py, tests
.github/         CI workflows
render.yaml      deployment
```

Milestones 0–2 are built (foundation, roles and sessions, events with Home, Calendar and the shared filter), plus the campus Map, Favorites (★ saved events, ♥ people), Add to calendar, Home time chips with Recommended (main events + your major), Hidden, Alerts, and all of Phase 2 (room approvals, room limits, reports and flags, moderation log, 150-day purge + Delete my account, terms note, extend series, offline). Next: real Microsoft sign-in and deploy. The Microsoft login waits on the Entra app registration; until then use the local developer sign-in.

## Getting started

Needs **Python 3.12** and **Node 22+**. No Docker.

```bash
cp .env.example .env              # defaults work for local dev
```

**Backend** (http://localhost:8000, health check at `/health`):

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m alembic upgrade head       # creates backend/dev.db (SQLite)
.venv/Scripts/python -m app.seed                   # the 4 test rooms
.venv/Scripts/python -m app.seed --demo            # optional: + demo people/events (prints dev sign-in emails)
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

**Frontend** (http://localhost:5173, in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

The top bar shows **API ok** when the frontend can reach the backend. Signed-out visitors only see the sign-in page; the **Sign in with Microsoft** button turns on once `MS_CLIENT_ID` / `MS_CLIENT_SECRET` / `OWNER_EMAIL` are in `.env` and the Microsoft login route lands. Roles and limits: edit `backend/app/core/permissions.py`. **Majors:** edit `backend/majors.txt`, one per line. New lines show up in the app right away, no restart (ADR-032).

**Turning on Sign in with Microsoft** (one time, in the [Entra admin center](https://entra.microsoft.com) → App registrations → New registration):
1. Name: the app's name. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts** (so the owner's personal account works; everyone else is still limited to WCC by the app).
2. Redirect URI: platform **Web**, `http://localhost:8000/auth/microsoft/callback` (add the production one later).
3. Copy the **Application (client) ID** into `MS_CLIENT_ID` in `.env`.
4. Certificates & secrets → New client secret → copy the **Value** into `MS_CLIENT_SECRET`.
5. Set `OWNER_EMAIL` and a long random `SESSION_SECRET` (e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`), then restart the API. The button turns on by itself.
6. Try a real `@my.sunywcc.edu` account. If it says **"Need admin approval"**, WCC IT has to grant consent once (architecture §8).

**Testing without Microsoft:** set `DEV_LOGIN=1` in `.env` (localhost only). The sign-in page then shows a "Local testing only" form: type a school email, pick a role, sign in. No passwords.

**Schema changes before launch:** there is one migration (ADR-022). After changing a model, delete `backend/migrations/versions/0001_initial_schema.py` and `backend/dev.db`, then run `alembic revision --autogenerate -m "initial schema" --rev-id 0001`, `alembic upgrade head`, and `python -m app.seed`. The frontend reads `VITE_API_BASE` (default `http://localhost:8000`); see `frontend/.env.example`.

In the Claude desktop app, `.claude/launch.json` has `api`, `web`, and `web-prod` (a production build preview, where the PWA/service worker is active; run `npm run build` first).

**Checks** (the same as CI; run only the side you changed):

| Side | Commands |
|---|---|
| backend | `ruff check .` · `python -m alembic check` · `python -m pytest -q` |
| frontend | `npm run lint` · `npm test` · `npm run build && npm run size` (fails over 150 KB gzipped first-load JS) |

### Changing the app name or icon

Both live in `frontend/brand/` (details in [frontend/brand/README.md](frontend/brand/README.md)). **Name:** edit `brand.json`; the top bar, sign-in page, browser tab, iOS title and PWA manifest all read it. **Icon:** replace `brand/icon.png` (square, ideally 1024 px), then run `python scripts/make-icons.py` from `frontend/` to regenerate every icon size and the favicon.

## Installing it on a phone or laptop

It's one web app (a PWA) for every device. Once it's online over HTTPS:

| Device | How to install |
|---|---|
| **iPhone / iPad** (Safari) | Share button → **Add to Home Screen**. The app shows this hint itself the first time. |
| **Android** (Chrome) and **Samsung** (Samsung Internet) | Tap **Install** in the app's hint, or the browser menu → **Install app** / **Add to Home screen**. |
| **Laptop** (Chrome, Edge) | The install icon in the address bar, or the app's **Install** hint. Safari and Firefox just use it as a website. |

Installed, it opens full screen with its own icon, follows the device's light/dark setting, and keeps the last events it loaded for when there's no signal.

## License

[CC BY-NC-ND 4.0](LICENSE) © Yosef Bunick. Contact the creator for commercial use or modified versions.
