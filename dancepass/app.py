"""Baila Caliente: a Punchpass-style app for Baila Caliente Dance Studios."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dancepass.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "BAILA_SECRET", os.environ.get("DANCEPASS_SECRET", "change-me-in-prod")
)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exc):  # noqa: ARG001
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    fresh = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    if fresh:
        _seed(conn)
    conn.commit()
    conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    """Seed Baila Caliente's current packages. More can be added later."""
    conn.executemany(
        "INSERT INTO pass_types (name, kind, punches, valid_days, price_cents) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            # $12 single class, $20 for two classes the same night.
            ("Single Class", "punch", 1, 60, 1200),
            ("Two Classes (Same Night)", "punch", 2, 1, 2000),
        ],
    )


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

@app.template_filter("money")
def fmt_money(cents: int | None) -> str:
    if cents is None:
        return "—"
    return f"${cents / 100:,.2f}"


@app.template_filter("dt")
def fmt_dt(value: str | None) -> str:
    if not value:
        return ""
    try:
        d = datetime.fromisoformat(value)
    except ValueError:
        return value
    return d.strftime("%a %b %d, %Y · %-I:%M %p")


@app.template_filter("d")
def fmt_d(value: str | None) -> str:
    if not value:
        return ""
    try:
        d = datetime.fromisoformat(value)
    except ValueError:
        return value
    return d.strftime("%b %d, %Y")


@app.context_processor
def inject_globals():
    return {"now": datetime.now()}


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

def pass_status(p: sqlite3.Row) -> str:
    """Active / Expired / Used up."""
    if p["expires_at"]:
        try:
            if datetime.fromisoformat(p["expires_at"]) < datetime.now():
                return "Expired"
        except ValueError:
            pass
    if p["punches_total"] is not None:
        remaining = p["punches_total"] - p["punches_used"]
        if remaining <= 0:
            return "Used up"
    return "Active"


def pass_remaining(p: sqlite3.Row) -> str:
    if p["punches_total"] is None:
        return "Unlimited"
    return f"{p['punches_total'] - p['punches_used']} / {p['punches_total']}"


def usable_passes_for(student_id: int) -> list[sqlite3.Row]:
    """Return passes that can still be used to check the student in."""
    db = get_db()
    rows = db.execute(
        """
        SELECT p.*, pt.name AS pass_type_name, pt.kind AS pass_kind
        FROM passes p
        JOIN pass_types pt ON pt.id = p.pass_type_id
        WHERE p.student_id = ?
        ORDER BY p.purchased_at DESC
        """,
        (student_id,),
    ).fetchall()
    return [r for r in rows if pass_status(r) == "Active"]


app.jinja_env.globals.update(
    pass_status=pass_status,
    pass_remaining=pass_remaining,
)


# ---------------------------------------------------------------------------
# Routes – dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    db = get_db()
    today = datetime.now().date().isoformat()
    week_end = (datetime.now() + timedelta(days=7)).isoformat()

    upcoming = db.execute(
        """
        SELECT cs.*,
               (SELECT COUNT(*) FROM attendance a WHERE a.session_id = cs.id) AS attended
        FROM class_sessions cs
        WHERE cs.starts_at >= ?
        ORDER BY cs.starts_at ASC
        LIMIT 8
        """,
        (today,),
    ).fetchall()

    stats = {
        "students": db.execute("SELECT COUNT(*) c FROM students").fetchone()["c"],
        "classes_week": db.execute(
            "SELECT COUNT(*) c FROM class_sessions WHERE starts_at >= ? AND starts_at <= ?",
            (today, week_end),
        ).fetchone()["c"],
        "active_passes": 0,
        "checkins_today": db.execute(
            "SELECT COUNT(*) c FROM attendance WHERE date(checked_in_at) = date('now')",
        ).fetchone()["c"],
    }
    all_passes = db.execute("SELECT * FROM passes").fetchall()
    stats["active_passes"] = sum(1 for p in all_passes if pass_status(p) == "Active")

    return render_template("dashboard.html", upcoming=upcoming, stats=stats)


# ---------------------------------------------------------------------------
# Routes – students
# ---------------------------------------------------------------------------

@app.route("/students")
def students_list():
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        rows = db.execute(
            """
            SELECT * FROM students
            WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ?
            ORDER BY last_name, first_name
            """,
            (like, like, like, like),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM students ORDER BY last_name, first_name"
        ).fetchall()
    return render_template("students_list.html", students=rows, q=q)


@app.route("/students/new", methods=["GET", "POST"])
def student_new():
    if request.method == "POST":
        f = request.form
        if not f.get("first_name", "").strip() or not f.get("last_name", "").strip():
            flash("First and last name are required.", "error")
            return render_template("student_form.html", student=f, action="New Student")
        db = get_db()
        cur = db.execute(
            """
            INSERT INTO students (first_name, last_name, email, phone, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                f["first_name"].strip(),
                f["last_name"].strip(),
                f.get("email", "").strip() or None,
                f.get("phone", "").strip() or None,
                f.get("notes", "").strip() or None,
            ),
        )
        db.commit()
        flash("Student added.", "ok")
        return redirect(url_for("student_detail", student_id=cur.lastrowid))
    return render_template("student_form.html", student={}, action="New Student")


@app.route("/students/<int:student_id>")
def student_detail(student_id):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        abort(404)
    passes = db.execute(
        """
        SELECT p.*, pt.name AS pass_type_name, pt.kind AS pass_kind
        FROM passes p
        JOIN pass_types pt ON pt.id = p.pass_type_id
        WHERE p.student_id = ?
        ORDER BY p.purchased_at DESC
        """,
        (student_id,),
    ).fetchall()
    history = db.execute(
        """
        SELECT a.*, cs.name AS class_name, cs.starts_at AS class_starts_at
        FROM attendance a
        JOIN class_sessions cs ON cs.id = a.session_id
        WHERE a.student_id = ?
        ORDER BY a.checked_in_at DESC
        LIMIT 50
        """,
        (student_id,),
    ).fetchall()
    pass_types = db.execute(
        "SELECT * FROM pass_types WHERE active = 1 ORDER BY price_cents"
    ).fetchall()
    return render_template(
        "student_detail.html",
        student=student,
        passes=passes,
        history=history,
        pass_types=pass_types,
    )


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def student_edit(student_id):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        abort(404)
    if request.method == "POST":
        f = request.form
        db.execute(
            """
            UPDATE students
               SET first_name = ?, last_name = ?, email = ?, phone = ?, notes = ?
             WHERE id = ?
            """,
            (
                f["first_name"].strip(),
                f["last_name"].strip(),
                f.get("email", "").strip() or None,
                f.get("phone", "").strip() or None,
                f.get("notes", "").strip() or None,
                student_id,
            ),
        )
        db.commit()
        flash("Student updated.", "ok")
        return redirect(url_for("student_detail", student_id=student_id))
    return render_template("student_form.html", student=student, action="Edit Student")


@app.route("/students/<int:student_id>/delete", methods=["POST"])
def student_delete(student_id):
    db = get_db()
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    flash("Student removed.", "ok")
    return redirect(url_for("students_list"))


# ---------------------------------------------------------------------------
# Routes – classes
# ---------------------------------------------------------------------------

@app.route("/classes")
def classes_list():
    scope = request.args.get("scope", "upcoming")
    db = get_db()
    if scope == "past":
        rows = db.execute(
            """
            SELECT cs.*,
                   (SELECT COUNT(*) FROM attendance a WHERE a.session_id = cs.id) AS attended
            FROM class_sessions cs
            WHERE cs.starts_at < datetime('now')
            ORDER BY cs.starts_at DESC
            LIMIT 100
            """
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT cs.*,
                   (SELECT COUNT(*) FROM attendance a WHERE a.session_id = cs.id) AS attended
            FROM class_sessions cs
            WHERE cs.starts_at >= datetime('now', '-1 day')
            ORDER BY cs.starts_at ASC
            """
        ).fetchall()
    return render_template("classes_list.html", classes=rows, scope=scope)


@app.route("/classes/new", methods=["GET", "POST"])
def class_new():
    if request.method == "POST":
        f = request.form
        if not f.get("name", "").strip() or not f.get("starts_at", "").strip():
            flash("Class name and start time are required.", "error")
            return render_template("class_form.html", cls=f, action="New Class")
        db = get_db()
        cur = db.execute(
            """
            INSERT INTO class_sessions
                (name, style, level, instructor, starts_at, duration_min,
                 capacity, location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f["name"].strip(),
                f.get("style", "Salsa").strip() or "Salsa",
                f.get("level", "").strip() or None,
                f.get("instructor", "").strip() or None,
                f["starts_at"].strip(),
                int(f.get("duration_min") or 60),
                int(f["capacity"]) if f.get("capacity") else None,
                f.get("location", "").strip() or None,
                f.get("notes", "").strip() or None,
            ),
        )
        db.commit()
        flash("Class scheduled.", "ok")
        return redirect(url_for("class_detail", session_id=cur.lastrowid))
    return render_template("class_form.html", cls={}, action="New Class")


@app.route("/classes/<int:session_id>")
def class_detail(session_id):
    db = get_db()
    cls = db.execute(
        "SELECT * FROM class_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not cls:
        abort(404)
    attendees = db.execute(
        """
        SELECT a.*, s.first_name, s.last_name,
               pt.name AS pass_type_name
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        LEFT JOIN passes p ON p.id = a.pass_id
        LEFT JOIN pass_types pt ON pt.id = p.pass_type_id
        WHERE a.session_id = ?
        ORDER BY a.checked_in_at ASC
        """,
        (session_id,),
    ).fetchall()
    not_checked_in = db.execute(
        """
        SELECT s.* FROM students s
        WHERE s.id NOT IN (SELECT student_id FROM attendance WHERE session_id = ?)
        ORDER BY s.last_name, s.first_name
        """,
        (session_id,),
    ).fetchall()
    return render_template(
        "class_detail.html",
        cls=cls,
        attendees=attendees,
        not_checked_in=not_checked_in,
    )


@app.route("/classes/<int:session_id>/edit", methods=["GET", "POST"])
def class_edit(session_id):
    db = get_db()
    cls = db.execute(
        "SELECT * FROM class_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not cls:
        abort(404)
    if request.method == "POST":
        f = request.form
        db.execute(
            """
            UPDATE class_sessions
               SET name = ?, style = ?, level = ?, instructor = ?,
                   starts_at = ?, duration_min = ?, capacity = ?,
                   location = ?, notes = ?
             WHERE id = ?
            """,
            (
                f["name"].strip(),
                f.get("style", "Salsa").strip() or "Salsa",
                f.get("level", "").strip() or None,
                f.get("instructor", "").strip() or None,
                f["starts_at"].strip(),
                int(f.get("duration_min") or 60),
                int(f["capacity"]) if f.get("capacity") else None,
                f.get("location", "").strip() or None,
                f.get("notes", "").strip() or None,
                session_id,
            ),
        )
        db.commit()
        flash("Class updated.", "ok")
        return redirect(url_for("class_detail", session_id=session_id))
    return render_template("class_form.html", cls=cls, action="Edit Class")


@app.route("/classes/<int:session_id>/delete", methods=["POST"])
def class_delete(session_id):
    db = get_db()
    db.execute("DELETE FROM class_sessions WHERE id = ?", (session_id,))
    db.commit()
    flash("Class removed.", "ok")
    return redirect(url_for("classes_list"))


# ---------------------------------------------------------------------------
# Routes – check-in / attendance
# ---------------------------------------------------------------------------

@app.route("/classes/<int:session_id>/checkin", methods=["POST"])
def checkin(session_id):
    db = get_db()
    cls = db.execute(
        "SELECT * FROM class_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not cls:
        abort(404)

    student_id = request.form.get("student_id", type=int)
    if not student_id:
        flash("Pick a student to check in.", "error")
        return redirect(url_for("class_detail", session_id=session_id))

    existing = db.execute(
        "SELECT id FROM attendance WHERE student_id = ? AND session_id = ?",
        (student_id, session_id),
    ).fetchone()
    if existing:
        flash("That student is already checked in.", "error")
        return redirect(url_for("class_detail", session_id=session_id))

    if cls["capacity"]:
        attended = db.execute(
            "SELECT COUNT(*) c FROM attendance WHERE session_id = ?",
            (session_id,),
        ).fetchone()["c"]
        if attended >= cls["capacity"]:
            flash("Class is at capacity.", "error")
            return redirect(url_for("class_detail", session_id=session_id))

    # Pick the best usable pass: punch cards first (use them up), then
    # memberships. Among punch cards, the one expiring soonest goes first.
    usable = usable_passes_for(student_id)
    pass_id = None
    chosen = None
    if usable:
        punch = sorted(
            [p for p in usable if p["punches_total"] is not None],
            key=lambda p: (p["expires_at"] or "9999"),
        )
        membership = [p for p in usable if p["punches_total"] is None]
        chosen = (punch + membership)[0]
        pass_id = chosen["id"]

    if chosen and chosen["punches_total"] is not None:
        db.execute(
            "UPDATE passes SET punches_used = punches_used + 1 WHERE id = ?",
            (chosen["id"],),
        )

    db.execute(
        """
        INSERT INTO attendance (student_id, session_id, pass_id)
        VALUES (?, ?, ?)
        """,
        (student_id, session_id, pass_id),
    )
    db.commit()

    if pass_id is None:
        flash("Checked in (no active pass — student owes a drop-in).", "warn")
    else:
        flash("Checked in.", "ok")
    return redirect(url_for("class_detail", session_id=session_id))


@app.route("/attendance/<int:attendance_id>/undo", methods=["POST"])
def checkin_undo(attendance_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM attendance WHERE id = ?", (attendance_id,)
    ).fetchone()
    if not row:
        abort(404)
    if row["pass_id"]:
        # Refund the punch if applicable.
        p = db.execute("SELECT * FROM passes WHERE id = ?", (row["pass_id"],)).fetchone()
        if p and p["punches_total"] is not None and p["punches_used"] > 0:
            db.execute(
                "UPDATE passes SET punches_used = punches_used - 1 WHERE id = ?",
                (p["id"],),
            )
    db.execute("DELETE FROM attendance WHERE id = ?", (attendance_id,))
    db.commit()
    flash("Check-in undone.", "ok")
    return redirect(url_for("class_detail", session_id=row["session_id"]))


# ---------------------------------------------------------------------------
# Routes – pass types & sales
# ---------------------------------------------------------------------------

@app.route("/passes")
def pass_types_list():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM pass_types ORDER BY active DESC, price_cents ASC"
    ).fetchall()
    return render_template("pass_types.html", pass_types=rows)


@app.route("/passes/new", methods=["GET", "POST"])
def pass_type_new():
    if request.method == "POST":
        f = request.form
        kind = f.get("kind", "punch")
        if kind not in ("punch", "membership"):
            flash("Invalid pass kind.", "error")
            return render_template("pass_type_form.html", pt=f, action="New Pass Type")
        db = get_db()
        db.execute(
            """
            INSERT INTO pass_types (name, kind, punches, valid_days, price_cents, active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f["name"].strip(),
                kind,
                int(f["punches"]) if kind == "punch" and f.get("punches") else None,
                int(f["valid_days"]) if f.get("valid_days") else None,
                int(round(float(f.get("price") or 0) * 100)),
                1 if f.get("active") else 0,
            ),
        )
        db.commit()
        flash("Pass type created.", "ok")
        return redirect(url_for("pass_types_list"))
    return render_template(
        "pass_type_form.html", pt={"active": 1}, action="New Pass Type"
    )


@app.route("/passes/<int:pass_type_id>/toggle", methods=["POST"])
def pass_type_toggle(pass_type_id):
    db = get_db()
    pt = db.execute("SELECT * FROM pass_types WHERE id = ?", (pass_type_id,)).fetchone()
    if not pt:
        abort(404)
    db.execute(
        "UPDATE pass_types SET active = ? WHERE id = ?",
        (0 if pt["active"] else 1, pass_type_id),
    )
    db.commit()
    return redirect(url_for("pass_types_list"))


@app.route("/students/<int:student_id>/sell", methods=["POST"])
def sell_pass(student_id):
    db = get_db()
    student = db.execute(
        "SELECT id FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if not student:
        abort(404)
    pt_id = request.form.get("pass_type_id", type=int)
    pt = db.execute("SELECT * FROM pass_types WHERE id = ?", (pt_id,)).fetchone()
    if not pt:
        flash("Pick a pass to sell.", "error")
        return redirect(url_for("student_detail", student_id=student_id))

    expires_at = None
    if pt["valid_days"]:
        expires_at = (datetime.now() + timedelta(days=pt["valid_days"])).isoformat(
            timespec="seconds"
        )

    db.execute(
        """
        INSERT INTO passes
            (student_id, pass_type_id, expires_at, punches_total, price_cents, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            student_id,
            pt["id"],
            expires_at,
            pt["punches"],
            pt["price_cents"],
            request.form.get("note", "").strip() or None,
        ),
    )
    db.commit()
    flash(f"Sold: {pt['name']}.", "ok")
    return redirect(url_for("student_detail", student_id=student_id))


@app.route("/passes/sold/<int:pass_id>/delete", methods=["POST"])
def sold_pass_delete(pass_id):
    db = get_db()
    p = db.execute("SELECT * FROM passes WHERE id = ?", (pass_id,)).fetchone()
    if not p:
        abort(404)
    db.execute("DELETE FROM passes WHERE id = ?", (pass_id,))
    db.commit()
    flash("Pass deleted.", "ok")
    return redirect(url_for("student_detail", student_id=p["student_id"]))


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
