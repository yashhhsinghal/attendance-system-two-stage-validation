# Real-Time Attendance Management System using Two-Stage Validation

An automated attendance system that combines **face recognition** with a simulated **RFID-based validation** mechanism to ensure accurate and reliable attendance tracking.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       PIPELINE OVERVIEW                         │
├─────────────┬───────────────────────────────────────────────────┤
│  Stage 0    │  encode_faces.py                                  │
│  (Pre-proc) │  Encode Dataset/ images → face_encodings.pkl      │
├─────────────┼───────────────────────────────────────────────────┤
│  Stage 1    │  simulate_rfid.py                                 │
│  (RFID)     │  Simulate door-swipe → rfid_entry_log.csv         │
├─────────────┼───────────────────────────────────────────────────┤
│  Stage 2    │  recognize_and_mark.py                            │
│  (Face Rec) │  CNN detection on Class_images/ → per-student     │
│             │  detection counts                                 │
├─────────────┼───────────────────────────────────────────────────┤
│  Stage 3    │  main.py  (Dual Validation — AND Logic)           │
│  (Decision) │  Present = RFID ✔  AND  Face ≥ 2 detections ✔    │
│             │  Output → attendance.csv                          │
└─────────────┴───────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
Attempt1/
├── main.py                  # Full pipeline — run this
├── capture_faces.py         # Webcam tool to capture student face images
├── encode_faces.py          # Encode faces → face_encodings.pkl
├── simulate_rfid.py         # Generate simulated RFID entry log
├── recognize_and_mark.py    # Face recognition on classroom images
├── camera_test.py           # Quick webcam test
│
├── Dataset/                 # Student face images (one folder per student)
│   ├── Krish/
│   ├── Prem/
│   ├── Vaishnavi/
│   └── Yash/
│
├── Class_images/            # Classroom photos to scan for faces
│   ├── img1.jpg
│   ├── img2.jpg
│   ├── img3.jpg
│   └── img4.jpg
│
├── attendance.csv           # Final output (generated)
├── rfid_entry_log.csv       # Simulated RFID log (generated)
├── face_encodings.pkl       # Cached face encodings (generated)
└── attendance_env/          # Python virtual environment
```

## 🚀 Quick Start

### 1. Activate the virtual environment

```bash
source attendance_env/bin/activate
```

### 2. (Optional) Capture more face images

```bash
python capture_faces.py
```

### 3. Run the full pipeline

```bash
# Interactive mode — you choose who swiped RFID
python main.py

# OR — assume all students swiped RFID
python main.py --rfid-all

# OR — skip re-encoding faces (faster if Dataset hasn't changed)
python main.py --skip-encode --rfid-all
```

### 4. Check the output

The final attendance is in `attendance.csv` with columns:
| Name | RFID_Swiped | Face_Detections | Face_Recognized | Final_Status | Timestamp |

## 🔧 Running Individual Stages

```bash
# Stage 0: Encode faces
python encode_faces.py

# Stage 1: Simulate RFID
python simulate_rfid.py         # interactive
python simulate_rfid.py --all   # all students

# Stage 2: Face recognition only
python recognize_and_mark.py
```

## ⚙️ Configuration

Key parameters can be tuned in each script:

| Parameter | File | Default | Description |
|-----------|------|---------|-------------|
| `THRESHOLD` | recognize_and_mark.py | 0.6 | Face distance threshold (lower = stricter) |
| `MIN_DETECTIONS` | main.py | 2 | Min face detections to pass Stage 2 |
| `model` | recognize_and_mark.py | `"cnn"` | Face detection model (`"cnn"` or `"hog"`) |

## 🛠️ Dependencies

- Python 3.10
- OpenCV (`opencv-python`)
- `face_recognition` (with `dlib`)
- NumPy
- pandas
- cmake

All are installed in the `attendance_env/` virtual environment.

## 📌 Dual Validation Logic

```
Student marked PRESENT only if:
    ┌──────────────────────────┐     ┌──────────────────────────┐
    │  Stage 1: RFID           │     │  Stage 2: Face Recog     │
    │  Student swiped at door  │ AND │  Detected ≥ 2 times      │
    │  (rfid_entry_log.csv)    │     │  in classroom images     │
    └──────────────────────────┘     └──────────────────────────┘
                         │                       │
                         └───────────┬───────────┘
                                     │
                              ┌──────▼──────┐
                              │   PRESENT   │
                              └─────────────┘
```

This **AND logic** prevents:
- **Proxy attendance**: A student's RFID is swiped but they aren't physically in the room
- **False positives**: A student is in the room but didn't officially register via RFID
