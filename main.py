"""
main.py — Real-Time Attendance Management System using Two-Stage Validation
=============================================================================

Pipeline:
  Stage 0  →  encode_faces.py        Pre-encode dataset faces (run once)
  Stage 1  →  simulate_rfid.py       Simulate RFID door-swipe log
  Stage 2  →  recognize_and_mark.py  Detect & recognize faces in classroom images
  Stage 3  →  THIS FILE              Dual-validation (AND logic) + final CSV

Dual-Validation (AND Logic):
  A student is marked PRESENT only if BOTH conditions are satisfied:
    1. Their RFID tag was swiped at the classroom door  (Stage 1)
    2. Their face was detected in ≥ MIN_DETECTIONS classroom images  (Stage 2)

Usage:
    python main.py                   # full pipeline (interactive RFID)
    python main.py --rfid-all        # full pipeline (all students swiped)
    python main.py --skip-encode     # skip re-encoding faces
"""

import os
import sys
import csv
from datetime import datetime
import pandas as pd

# ─── Project modules ─────────────────────────────────────────────────────────
from encode_faces import encode_faces
from simulate_rfid import simulate_rfid, get_student_names
from recognize_and_mark import recognize_faces_in_classroom

# ─── Configuration ────────────────────────────────────────────────────────────
RFID_LOG_FILE = "rfid_entry_log.csv"
ATTENDANCE_FILE = "attendance.csv"
MIN_DETECTIONS = 2   # Minimum face-detection count to pass Stage 2
# ──────────────────────────────────────────────────────────────────────────────


def load_rfid_log(filepath=RFID_LOG_FILE):
    """Read RFID entry log and return the set of student names who swiped."""
    if not os.path.exists(filepath):
        print(f"  ⚠ RFID log file not found: {filepath}")
        return set()

    swiped = set()
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            swiped.add(row["Student_Name"])

    return swiped


def dual_validate(rfid_set, face_counter, all_students, min_detections=MIN_DETECTIONS):
    """
    Apply AND-logic to produce the final attendance.

    Parameters
    ----------
    rfid_set       : set[str]   — students who swiped RFID
    face_counter   : dict[str, int] — face-detection counts per student
    all_students   : set[str]   — full roster of known students
    min_detections : int        — threshold for face recognition stage

    Returns
    -------
    list[dict] — one row per student with validation details
    """
    results = []

    for name in sorted(all_students):
        rfid_ok = name in rfid_set
        face_count = face_counter.get(name, 0)
        face_ok = face_count >= min_detections

        # ── AND logic ─────────────────────────────────────────────────────
        final_status = "Present" if (rfid_ok and face_ok) else "Absent"

        results.append({
            "Name": name,
            "RFID_Swiped": "Yes" if rfid_ok else "No",
            "Face_Detections": face_count,
            "Face_Recognized": "Yes" if face_ok else "No",
            "Final_Status": final_status,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    return results


def print_results(results):
    """Pretty-print the dual-validation results."""
    header = f"  {'Name':15s} | {'RFID':5s} | {'Face Det.':9s} | {'Face OK':7s} | {'STATUS':8s}"
    sep = "  " + "─" * len(header)

    print(sep)
    print(header)
    print(sep)

    for r in results:
        emoji = "✅" if r["Final_Status"] == "Present" else "❌"
        print(
            f"  {r['Name']:15s} | {r['RFID_Swiped']:5s} | "
            f"{r['Face_Detections']:^9d} | {r['Face_Recognized']:7s} | "
            f"{emoji} {r['Final_Status']}"
        )

    print(sep)


def save_attendance(results, filepath=ATTENDANCE_FILE):
    """Save the final attendance to a CSV."""
    df = pd.DataFrame(results)
    df.to_csv(filepath, index=False)
    print(f"\n  ✅ Final attendance saved to {filepath}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def main():
    skip_encode = "--skip-encode" in sys.argv
    rfid_all = "--rfid-all" in sys.argv

    print("=" * 65)
    print("  Real-Time Attendance System — Two-Stage Validation")
    print("=" * 65)

    # ── Stage 0: Encode faces ─────────────────────────────────────────────
    if not skip_encode:
        print("\n── Stage 0: Encoding Faces ──\n")
        encode_faces()
    else:
        print("\n── Stage 0: Skipped (using cached encodings) ──\n")

    # ── Stage 1: RFID simulation ─────────────────────────────────────────
    print("\n── Stage 1: RFID Entry Simulation ──\n")
    if rfid_all:
        simulate_rfid(get_student_names())
    else:
        simulate_rfid()

    rfid_set = load_rfid_log()
    print(f"  Students with RFID entry: {sorted(rfid_set)}")

    # ── Stage 2: Face recognition ────────────────────────────────────────
    print("\n── Stage 2: Face Recognition (CNN) ──\n")
    face_counter, all_students = recognize_faces_in_classroom()

    print("\n  Detection summary:")
    for name in sorted(all_students):
        print(f"    {name}: detected {face_counter.get(name, 0)} time(s)")

    # ── Stage 3: Dual validation (AND logic) ─────────────────────────────
    print("\n── Stage 3: Dual Validation (AND Logic) ──\n")
    print("  Rule: Present = RFID_Swiped ✔  AND  Face_Detections ≥ "
          f"{MIN_DETECTIONS} ✔\n")

    results = dual_validate(rfid_set, face_counter, all_students)
    print_results(results)
    save_attendance(results)

    # ── Summary ──────────────────────────────────────────────────────────
    present = sum(1 for r in results if r["Final_Status"] == "Present")
    absent = len(results) - present
    print(f"\n  📊  Present: {present}  |  Absent: {absent}  |  Total: {len(results)}")
    print("\n" + "=" * 65)
    print("  Process Completed")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
