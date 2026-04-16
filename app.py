"""
app.py — Teacher Dashboard for Attendance Management
=====================================================
A Flask web application that lets teachers:
  • View the dashboard with overall attendance statistics
  • See per-student attendance percentage and history
  • Manually mark/override attendance for a student on a date
  • Run the attendance pipeline from the browser
  • Login/logout with a simple password

Usage:
    python app.py
    → Open http://localhost:5000 in your browser
"""

import os
import csv
import sqlite3
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g, jsonify
)

# ─── Configuration ────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "attendance-secret-key-change-in-production"

# Session / cookie settings
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_NAME"] = "attendance_session"

DATABASE = "attendance.db"
DATASET_DIR = "Dataset"
ATTENDANCE_CSV = "attendance.csv"

# Default teacher credentials (change these!)
TEACHER_USERNAME = "admin"
TEACHER_PASSWORD = "admin123"
# ──────────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_db():
    """Get a database connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables if they don't exist."""
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            date        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'Absent',
            rfid_swiped TEXT DEFAULT 'No',
            face_detections INTEGER DEFAULT 0,
            source      TEXT DEFAULT 'system',
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE(student_id, date)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            date        TEXT NOT NULL,
            old_status  TEXT,
            new_status  TEXT,
            reason      TEXT,
            changed_by  TEXT DEFAULT 'teacher',
            changed_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        );
    """)
    db.commit()


def sync_students_from_dataset():
    """Ensure all students from Dataset/ folder exist in the database."""
    db = get_db()
    if not os.path.isdir(DATASET_DIR):
        return

    for name in sorted(os.listdir(DATASET_DIR)):
        if os.path.isdir(os.path.join(DATASET_DIR, name)) and not name.startswith("."):
            db.execute(
                "INSERT OR IGNORE INTO students (name) VALUES (?)", (name,)
            )
    db.commit()


def import_csv_attendance():
    """Import attendance.csv (from pipeline) into the database."""
    if not os.path.exists(ATTENDANCE_CSV):
        return 0

    db = get_db()
    imported = 0

    with open(ATTENDANCE_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            if not name:
                continue

            # Get or create student
            student = db.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()
            if not student:
                db.execute("INSERT INTO students (name) VALUES (?)", (name,))
                student = db.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()

            student_id = student["id"]
            today = date.today().isoformat()
            status = row.get("Final_Status", row.get("Status", "Absent"))
            rfid = row.get("RFID_Swiped", "N/A")
            face_det = int(row.get("Face_Detections", 0))

            # Insert or update
            existing = db.execute(
                "SELECT id, status FROM attendance WHERE student_id = ? AND date = ?",
                (student_id, today)
            ).fetchone()

            if existing:
                if existing["status"] != status:
                    db.execute(
                        "UPDATE attendance SET status=?, rfid_swiped=?, face_detections=?, source='system', updated_at=? WHERE id=?",
                        (status, rfid, face_det, datetime.now().isoformat(), existing["id"])
                    )
            else:
                db.execute(
                    "INSERT INTO attendance (student_id, date, status, rfid_swiped, face_detections, source) VALUES (?,?,?,?,?,?)",
                    (student_id, today, status, rfid, face_det, "system")
                )
                imported += 1

    db.commit()
    return imported


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════════════════

def login_required(f):
    """Decorator to protect routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == TEACHER_USERNAME and password == TEACHER_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def dashboard():
    """Main dashboard — overview of today's attendance."""
    db = get_db()
    today = date.today().isoformat()

    students = db.execute("SELECT * FROM students ORDER BY name").fetchall()
    today_records = db.execute(
        """SELECT s.name, a.status, a.rfid_swiped, a.face_detections, a.source
           FROM students s
           LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
           ORDER BY s.name""",
        (today,)
    ).fetchall()

    total = len(students)
    present = sum(1 for r in today_records if r["status"] == "Present")
    absent = total - present

    # Percentage per student (all time)
    student_stats = []
    for s in students:
        total_days = db.execute(
            "SELECT COUNT(*) as cnt FROM attendance WHERE student_id = ?", (s["id"],)
        ).fetchone()["cnt"]
        present_days = db.execute(
            "SELECT COUNT(*) as cnt FROM attendance WHERE student_id = ? AND status = 'Present'",
            (s["id"],)
        ).fetchone()["cnt"]
        pct = round((present_days / total_days * 100), 1) if total_days > 0 else 0.0
        student_stats.append({
            "id": s["id"],
            "name": s["name"],
            "total_days": total_days,
            "present_days": present_days,
            "percentage": pct,
        })

    return render_template(
        "dashboard.html",
        today=today,
        today_records=today_records,
        total=total,
        present=present,
        absent=absent,
        student_stats=student_stats,
    )


@app.route("/student/<int:student_id>")
@login_required
def student_detail(student_id):
    """Detailed attendance history for one student."""
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("dashboard"))

    records = db.execute(
        """SELECT date, status, rfid_swiped, face_detections, source, updated_at
           FROM attendance WHERE student_id = ? ORDER BY date DESC""",
        (student_id,)
    ).fetchall()

    total = len(records)
    present = sum(1 for r in records if r["status"] == "Present")
    pct = round((present / total * 100), 1) if total > 0 else 0.0

    # Audit log for this student
    audit = db.execute(
        """SELECT date, old_status, new_status, reason, changed_at
           FROM audit_log WHERE student_id = ? ORDER BY changed_at DESC""",
        (student_id,)
    ).fetchall()

    return render_template(
        "student_detail.html",
        student=student,
        records=records,
        total=total,
        present=present,
        percentage=pct,
        audit=audit,
    )


@app.route("/edit_attendance", methods=["GET", "POST"])
@login_required
def edit_attendance():
    """Manually add or change attendance for a student."""
    db = get_db()
    students = db.execute("SELECT * FROM students ORDER BY name").fetchall()

    if request.method == "POST":
        student_id = int(request.form["student_id"])
        att_date = request.form["date"]
        new_status = request.form["status"]
        reason = request.form.get("reason", "").strip()

        student = db.execute("SELECT name FROM students WHERE id = ?", (student_id,)).fetchone()

        # Check for existing record
        existing = db.execute(
            "SELECT id, status FROM attendance WHERE student_id = ? AND date = ?",
            (student_id, att_date)
        ).fetchone()

        old_status = existing["status"] if existing else "No Record"

        if existing:
            db.execute(
                "UPDATE attendance SET status=?, source='manual', updated_at=? WHERE id=?",
                (new_status, datetime.now().isoformat(), existing["id"])
            )
        else:
            db.execute(
                "INSERT INTO attendance (student_id, date, status, source) VALUES (?,?,?,?)",
                (student_id, att_date, new_status, "manual")
            )

        # Audit log
        db.execute(
            "INSERT INTO audit_log (student_id, date, old_status, new_status, reason) VALUES (?,?,?,?,?)",
            (student_id, att_date, old_status, new_status, reason or "Manual override by teacher")
        )
        db.commit()

        flash(f"Attendance for {student['name']} on {att_date} set to {new_status}.", "success")
        return redirect(url_for("student_detail", student_id=student_id))

    return render_template("edit_attendance.html", students=students, today=date.today().isoformat())


@app.route("/import_csv")
@login_required
def import_csv():
    """Import latest attendance.csv from the pipeline."""
    with app.app_context():
        count = import_csv_attendance()
    if count > 0:
        flash(f"Imported {count} attendance record(s) from CSV.", "success")
    else:
        flash("No new records to import (already up to date or CSV not found).", "info")
    return redirect(url_for("dashboard"))


@app.route("/run_pipeline")
@login_required
def run_pipeline():
    """Trigger the attendance pipeline from the browser."""
    import subprocess
    python_path = os.path.join("attendance_env", "bin", "python")
    try:
        result = subprocess.run(
            [python_path, "main.py", "--skip-encode", "--rfid-all"],
            capture_output=True, text=True, timeout=300, cwd=os.path.dirname(__file__) or "."
        )
        if result.returncode == 0:
            # Auto-import results
            with app.app_context():
                import_csv_attendance()
            flash("Pipeline ran successfully! Attendance imported.", "success")
        else:
            flash(f"Pipeline error: {result.stderr[:500]}", "danger")
    except Exception as e:
        flash(f"Failed to run pipeline: {e}", "danger")

    return redirect(url_for("dashboard"))


@app.route("/audit_log")
@login_required
def audit_log():
    """View all manual changes."""
    db = get_db()
    logs = db.execute(
        """SELECT al.*, s.name as student_name
           FROM audit_log al
           JOIN students s ON al.student_id = s.id
           ORDER BY al.changed_at DESC"""
    ).fetchall()
    return render_template("audit_log.html", logs=logs)


# ═══════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

@app.before_request
def before_first_request_setup():
    """Initialize DB and sync students on first request."""
    if not getattr(app, '_db_initialized', False):
        init_db()
        sync_students_from_dataset()
        app._db_initialized = True


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_ENV") != "production"
    print("\n" + "=" * 55)
    print("  Teacher Attendance Dashboard")
    print(f"  Open: http://127.0.0.1:{port}")
    print("  Login: admin / admin123")
    print("=" * 55 + "\n")
    app.run(debug=debug, host="0.0.0.0", port=port)
