"""
recognize_and_mark.py
=====================
Stage 2: Face Recognition — Process classroom images, detect faces using
a CNN-based model, and count how many times each student is recognized.

This module can be used standalone or imported by the main pipeline.

Usage (standalone):
    python recognize_and_mark.py
"""

import os
import pickle
import cv2
import numpy as np
import face_recognition
from collections import defaultdict

# ─── Configuration ────────────────────────────────────────────────────────────
DATASET_DIR = "Dataset"
CLASS_IMAGES_DIR = "Class_images"
ENCODINGS_FILE = "face_encodings.pkl"
VALID_EXTENSIONS = (".jpg", ".jpeg", ".png")
THRESHOLD = 0.6        # Face-distance threshold (lower = stricter)
MIN_DETECTIONS = 2     # Minimum detections across images to count as "seen"
# ──────────────────────────────────────────────────────────────────────────────


def load_encodings():
    """Load pre-computed encodings from pickle, or build them on the fly."""
    if os.path.exists(ENCODINGS_FILE):
        print(f"  Loading cached encodings from {ENCODINGS_FILE}")
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
        return data["encodings"], data["names"]

    # Fallback: encode from Dataset/ directly
    print("  ⚠ No cached encodings found — encoding from Dataset/ ...")
    known_encodings = []
    known_names = []

    for person in sorted(os.listdir(DATASET_DIR)):
        person_path = os.path.join(DATASET_DIR, person)
        if not os.path.isdir(person_path):
            continue

        for img_name in sorted(os.listdir(person_path)):
            if img_name.startswith("."):
                continue
            if not img_name.lower().endswith(VALID_EXTENSIONS):
                continue

            img_path = os.path.join(person_path, img_name)
            try:
                image = face_recognition.load_image_file(img_path)
                image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(person)
            except Exception as e:
                print(f"    ⚠ Error processing {img_name}: {e}")

    return known_encodings, known_names


def recognize_faces_in_classroom():
    """
    Process every image in Class_images/ and return a dict
    mapping student name → number of images they were detected in.
    """

    known_encodings, known_names = load_encodings()
    print(f"  Total encodings loaded : {len(known_encodings)}")
    print(f"  Known people           : {sorted(set(known_names))}")

    attendance_counter = defaultdict(int)

    class_images = [
        f for f in sorted(os.listdir(CLASS_IMAGES_DIR))
        if not f.startswith(".") and f.lower().endswith(VALID_EXTENSIONS)
    ]

    if not class_images:
        print("  ⚠ No class images found in Class_images/")
        return dict(attendance_counter), set(known_names)

    print(f"\n  Processing {len(class_images)} classroom image(s)...\n")

    for img_name in class_images:
        img_path = os.path.join(CLASS_IMAGES_DIR, img_name)
        print(f"    📷  {img_name}")

        image = face_recognition.load_image_file(img_path)
        image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)

        # Use CNN model for robust multi-face detection
        locations = face_recognition.face_locations(image, model="cnn")
        encodings = face_recognition.face_encodings(image, locations)

        print(f"        Faces detected: {len(encodings)}")

        detected_in_this_image = set()

        for enc in encodings:
            face_distances = face_recognition.face_distance(known_encodings, enc)
            if len(face_distances) == 0:
                continue

            best_idx = np.argmin(face_distances)
            best_dist = face_distances[best_idx]

            if best_dist < THRESHOLD:
                name = known_names[best_idx]
                detected_in_this_image.add(name)

        print(f"        Recognized    : {detected_in_this_image or '{none}'}")

        for person in detected_in_this_image:
            attendance_counter[person] += 1

    return dict(attendance_counter), set(known_names)


# ─── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    import pandas as pd

    print("\n===== Face Recognition Stage =====\n")

    counter, all_students = recognize_faces_in_classroom()

    print("\n── Detection Counts ──")
    for name in sorted(all_students):
        count = counter.get(name, 0)
        status = "✔ Present" if count >= MIN_DETECTIONS else "✘ Absent"
        print(f"  {name:15s} → detected {count} time(s)  [{status}]")

    # Simple CSV (face-recognition only, no RFID)
    rows = []
    for name in sorted(all_students):
        count = counter.get(name, 0)
        rows.append({
            "Name": name,
            "Detections": count,
            "FR_Status": "Present" if count >= MIN_DETECTIONS else "Absent",
        })

    df = pd.DataFrame(rows)
    df.to_csv("face_recognition_results.csv", index=False)
    print("\n✅ Results saved to face_recognition_results.csv\n")
