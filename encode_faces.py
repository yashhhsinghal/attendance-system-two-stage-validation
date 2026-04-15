"""
encode_faces.py
===============
Stage 0: Pre-processing — Encode all known faces from the Dataset/ folder
and save them to a pickle file for fast reuse by the recognition pipeline.

Usage:
    python encode_faces.py
"""

import os
import pickle
import cv2
import face_recognition

# ─── Configuration ────────────────────────────────────────────────────────────
DATASET_DIR = "Dataset"
ENCODINGS_FILE = "face_encodings.pkl"
VALID_EXTENSIONS = (".jpg", ".jpeg", ".png")
# ──────────────────────────────────────────────────────────────────────────────

def encode_faces():
    """Walk through Dataset/<Name>/ folders and create 128-d face encodings."""

    known_encodings = []
    known_names = []

    print("\n===== Encoding Faces from Dataset =====\n")

    for person in sorted(os.listdir(DATASET_DIR)):
        person_path = os.path.join(DATASET_DIR, person)

        if not os.path.isdir(person_path):
            continue

        print(f"  Processing: {person}")
        count = 0

        for img_name in sorted(os.listdir(person_path)):
            # Skip hidden files (.DS_Store etc.)
            if img_name.startswith("."):
                continue
            if not img_name.lower().endswith(VALID_EXTENSIONS):
                continue

            img_path = os.path.join(person_path, img_name)

            try:
                image = face_recognition.load_image_file(img_path)
                # Resize for encoding stability
                image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)

                encodings = face_recognition.face_encodings(image)

                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(person)
                    count += 1
                else:
                    print(f"    ⚠ No face found in {img_name}")

            except Exception as e:
                print(f"    ⚠ Error processing {img_name}: {e}")

        print(f"    → {count} encoding(s) saved for {person}")

    # ── Save to disk ──────────────────────────────────────────────────────────
    data = {"encodings": known_encodings, "names": known_names}

    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)

    print(f"\n✅ Total encodings: {len(known_encodings)}")
    print(f"✅ Known people  : {sorted(set(known_names))}")
    print(f"✅ Saved to       : {ENCODINGS_FILE}\n")


if __name__ == "__main__":
    encode_faces()
