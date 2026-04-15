"""
capture_faces.py
================
Capture face images for a student using the webcam.
Images are saved to Dataset/<student_name>/ for use by the encoding pipeline.

Usage:
    python capture_faces.py

Controls:
    C  — Capture an image
    Q  — Quit
"""

import cv2
import os

DATASET_DIR = "Dataset"

def capture():
    name = input("Enter student name: ").strip()
    if not name:
        print("❌ Name cannot be empty.")
        return

    path = os.path.join(DATASET_DIR, name)
    os.makedirs(path, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot access the camera.")
        return

    count = len([f for f in os.listdir(path) if f.endswith(".jpg")])  # resume numbering
    print(f"\nCapturing images for '{name}' (saving to {path}/)")
    print("Press C to capture | Q to quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠ Camera read failed.")
            break

        # Show live preview with overlay
        display = frame.copy()
        cv2.putText(display, f"Student: {name}  |  Captured: {count}",
                     (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, "C = Capture  |  Q = Quit",
                     (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("Face Capture", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            filepath = os.path.join(path, f"{count}.jpg")
            cv2.imwrite(filepath, frame)
            print(f"  ✅ Saved image {count} → {filepath}")
            count += 1

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n📸 Total images captured for '{name}': {count}")


if __name__ == "__main__":
    capture()
