# Baila Caliente Dance Studios — Class Manager

A small, self-hosted Punchpass-style app for **Baila Caliente Dance Studios**
(Passion · Soul · Desire). Schedule Salsa & Bachata drop-in classes and the
monthly social, sign students' liability waivers, sell drop-in punches, and
check people in at the door.

## Features

- **Students** — names, contact info, notes, attendance history, **liability waiver** status.
- **Waivers** — students sign a typed-name liability waiver from their profile.
  Check-in is blocked until the waiver is on file.
- **Classes & Socials** — schedule sessions as either a regular **Class** or
  the monthly **Social**, with style (Salsa / Bachata / etc.), level,
  instructor, capacity, location.
- **Drop-in passes** — Baila Caliente runs on drop-ins, not memberships:
  - **Drop-In Class — $12** (one class)
  - **Monthly Social Entry — $15** (one social)
- **Sales** — sell a pass to a student in one click.
- **Check-in** — one-click check-in. The app auto-deducts a punch from the
  student's oldest active pass; **undo** refunds it. Unsigned-waiver students
  are sent back to their profile to sign.
- **Dashboard** — students, classes this week, active passes, today's check-ins.

Seeded on first run with Baila Caliente's offerings:
- **Drop-In Class — $12**
- **Monthly Social Entry — $15**

Add more packages on the Passes page as you launch them. The schema still
supports multi-class punch cards and date-bounded memberships if you ever want
them; the seed just keeps things lean for now.

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
