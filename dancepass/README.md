# DancePass

A small, self-hosted Punchpass-style app for managing your **Salsa & Bachata** students:
schedule classes, sell punch cards & memberships, and check students in at the door.

## Features

- **Students** — names, contact info, notes, attendance history.
- **Classes** — schedule sessions with style (Salsa / Bachata / etc.), level, instructor, capacity, location.
- **Passes** — two kinds:
  - **Punch cards** (e.g. 5-class pass, 10-class pass) with optional expiry.
  - **Memberships** (e.g. Monthly Unlimited) with a validity window.
- **Sales** — sell any active pass type to a student in one click.
- **Check-in** — one-click check-in. The app auto-picks the student's oldest active pass
  (punch cards before memberships) and deducts a punch. Undo refunds the punch.
- **Dashboard** — students, classes this week, active passes, today's check-ins.

Seeded on first run with sensible defaults: Drop-in, 5-Class Pass, 10-Class Pass,
Monthly Unlimited.

## Run it

Requires Python 3.10+.

```bash
cd dancepass
./run.sh
```

Then open http://localhost:5050.

The first run creates `dancepass.db` (SQLite) next to `app.py` and seeds default
pass types. The DB is the source of truth — back it up to keep your data.

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
  static/style.css  # Salsa-pink / Bachata-purple theme
```

## Notes

- Set `DANCEPASS_SECRET` in your environment for production sessions.
- The default port is 5050; change it in `run.sh` if needed.
- Single-user app: there's no login. Run it on a private network or behind your own auth.
