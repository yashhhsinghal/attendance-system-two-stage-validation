"""
simulate_rfid.py
================
Stage 1: RFID Simulation — Generate a simulated RFID entry log CSV.

In a real deployment an RFID reader at the classroom door would produce
these records.  Here we simulate them so the rest of the pipeline can
be tested without hardware.

Usage:
    python simulate_rfid.py          # interactive — choose who entered
    python simulate_rfid.py --all    # mark every student as entered
"""

import os
import sys
import csv
from datetime import datetime, timedelta
import random

# ─── Configuration ────────────────────────────────────────────────────────────
DATASET_DIR = "Dataset"
RFID_LOG_FILE = "rfid_entry_log.csv"
# ──────────────────────────────────────────────────────────────────────────────

# Simulated RFID-to-student mapping  (tag ID → name)
def _generate_rfid_tags(names):
    """Create a deterministic RFID tag for each student name."""
    tags = {}
    for i, name in enumerate(names):
        tag_id = f"RFID-{1001 + i:04d}"
        tags[name] = tag_id
    return tags


def get_student_names():
    """Read student names from the Dataset/ folder."""
    names = []
    for entry in sorted(os.listdir(DATASET_DIR)):
        if os.path.isdir(os.path.join(DATASET_DIR, entry)) and not entry.startswith("."):
            names.append(entry)
    return names


def simulate_rfid(selected_students=None):
    """
    Write an RFID entry-log CSV.

    Parameters
    ----------
    selected_students : list[str] or None
        Students who "swiped" at the door.  If None, ask interactively.
    """
    all_students = get_student_names()
    rfid_map = _generate_rfid_tags(all_students)

    if selected_students is None:
        # Interactive mode
        print("\n===== RFID Entry Simulation =====\n")
        print("Students in database:")
        for i, name in enumerate(all_students, 1):
            print(f"  {i}. {name}  (Tag: {rfid_map[name]})")

        print("\nEnter the numbers of students who swiped RFID (comma-separated)")
        print("Example: 1,3,4   or   'all' for everyone")
        choice = input("\n> ").strip().lower()

        if choice == "all":
            selected_students = all_students
        else:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
            selected_students = [all_students[i] for i in indices if 0 <= i < len(all_students)]

    # ── Generate timestamped entries ──────────────────────────────────────────
    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    entries = []

    for student in selected_students:
        # Random entry time within the first 15 minutes of class
        offset = timedelta(minutes=random.randint(0, 15), seconds=random.randint(0, 59))
        entry_time = base_time + offset
        entries.append({
            "RFID_Tag": rfid_map[student],
            "Student_Name": student,
            "Entry_Time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    # Sort by entry time
    entries.sort(key=lambda x: x["Entry_Time"])

    # ── Write CSV ─────────────────────────────────────────────────────────────
    with open(RFID_LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["RFID_Tag", "Student_Name", "Entry_Time"])
        writer.writeheader()
        writer.writerows(entries)

    print(f"\n✅ RFID log saved to {RFID_LOG_FILE}")
    print(f"   Students who swiped: {[e['Student_Name'] for e in entries]}\n")

    return entries


if __name__ == "__main__":
    if "--all" in sys.argv:
        names = get_student_names()
        simulate_rfid(names)
    else:
        simulate_rfid()
