# Baila Caliente Dance Studios — Class Manager

A small, self-hosted Punchpass-style app for **Baila Caliente Dance Studios**
(Passion · Soul · Desire). Schedule Salsa & Bachata classes, sell punch cards
and memberships, and check students in at the door.

## Features

- **Students** — names, contact info, notes, attendance history.
- **Classes** — schedule sessions with style (Salsa / Bachata / etc.), level, instructor, capacity, location.
- **Passes** — two kinds:
  - **Punch cards** (e.g. Single Class, Two-Class Night) with optional expiry.
  - **Memberships** (e.g. Monthly Unlimited) with a validity window.
- **Sales** — sell any active pass type to a student in one click.
- **Check-in** — one-click check-in. The app auto-picks the student's oldest active pass
  (punch cards before memberships) and deducts a punch. Undo refunds the punch.
- **Dashboard** — students, classes this week, active passes, today's check-ins.

Seeded on first run with Baila Caliente's current packages:
- **Single Class — $12** (1 punch, 60-day expiry)
- **Two Classes, Same Night — $20** (2 punches, 1-day expiry to encourage same-night use)

Add more packages on the Passes page as you launch them.

## Run it

Requires Python 3.10+.

```bash
cd dancepass
./run.sh
```

Then open http://localhost:5050.

The first run creates `dancepass.db` (SQLite) next to `app.py` and seeds the
two starter pass types. The DB is the source of truth — back it up to keep
your data.

## Branding

The studio logo lives at `static/logo.svg` as a placeholder. To use your real
logo, drop a PNG (any size, square works best) at `static/logo.png` — the
topbar will pick it up automatically and fall back to the SVG if the PNG isn't
there. Colors are ruby red (`#c8102e`), black, and white; tweak them in
`static/style.css` (`:root` block) if needed.

## Manual setup (alternative)

```bash
cd dancepass
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
FLASK_APP=app.py flask run --host 0.0.0.0 --port 5050
```

## Layout

```
dancepass/
  app.py            # Flask app: routes, db helpers, domain logic
  schema.sql        # SQLite schema
  requirements.txt  # Flask
  run.sh            # venv + install + run
  templates/        # Jinja2 templates
  static/
    style.css       # Black / white / ruby red theme
    logo.svg        # Placeholder; replaced by logo.png when present
```

## Notes

- Set `BAILA_SECRET` (or `DANCEPASS_SECRET`) in your environment for production sessions.
- The default port is 5050; change it in `run.sh` if needed.
- Single-user app: there's no login yet (planned for v2). Run it on a private network or behind your own auth.
