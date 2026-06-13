# 🏋️ AI Real-time GYM Coach

An AI-powered real-time gym coaching application that uses your webcam to analyze exercise form, count reps and sets, and deliver live voice feedback through a conversational AI coach — all running in your browser.

---

## What It Does

- Detects your body pose in real-time using your webcam
- Automatically counts reps and tracks sets for 5 exercises
- Scores your form on every frame (0–100%) and changes the skeleton color based on form quality
- Speaks coaching cues aloud using an AI language model and text-to-speech
- Welcomes you by name when you log in
- Saves your workout history to a local database and visualizes it as a bar chart
- Shows a post-session summary card with total reps, sets, and form score

---

## Exercises Supported

| Exercise | What It Tracks |
|---|---|
| Squats | Knee angle, back angle, depth status |
| Push-ups | Elbow angle, body alignment, hip position |
| Biceps Curls (Dumbbell) | Elbow angle, elbow drift, torso swing |
| Shoulder Press | Elbow angle, arm extension, back arch |
| Lunges | Front knee angle, torso angle, lateral balance |

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI & App Framework | Streamlit |
| Real-time Video | streamlit-webrtc + WebRTC |
| Pose Detection | MediaPipe Pose Landmarker (Full model) |
| Video Processing | OpenCV |
| AI Coach LLM | Groq API — `llama-3.3-70b-versatile` |
| Text-to-Speech | gTTS (Google Text-to-Speech) |
| Database | SQLite (local) |
| Environment Config | python-dotenv |

---

## Project Structure

```
AI-REALTIME-GYM-COACH/
│
├── main.py                          # App entry point, Streamlit UI
│
├── core/
│   └── base_exercise.py             # Abstract base class for all detectors
│
├── detectors/
│   ├── squat.py                     # Squat rep counter + form analysis
│   ├── pushup.py                    # Push-up rep counter + form analysis
│   ├── biceps_curl.py               # Biceps curl rep counter + form analysis
│   ├── shoulder_press.py            # Shoulder press rep counter + form analysis
│   └── lunges.py                    # Lunges rep counter + form analysis
│
├── ml_models/
│   └── pose_landmarker_full.task    # MediaPipe pose landmark model
│
├── services/
│   ├── auth/
│   │   └── login_wall.py            # Username-based login, creates user in DB
│   │
│   ├── coaching/
│   │   ├── llm.py                   # Groq LLM client wrapper
│   │   ├── tts.py                   # gTTS text-to-speech wrapper
│   │   └── voice_pipeline.py        # Orchestrates when and what to speak
│   │
│   ├── config/
│   │   └── workout_config.py        # Exercise options, pose connections,
│   │                                  form scoring, LLM prompt, skeleton colors
│   │
│   ├── persistence/
│   │   └── exercise_repository.py   # SQLite CRUD for users and workout history
│   │
│   ├── state/
│   │   └── session_defaults.py      # Streamlit session state initialization
│   │
│   ├── tracking/
│   │   └── metrics.py               # Syncs video metrics to session state,
│   │                                  triggers voice events
│   │
│   ├── ui/
│   │   └── style_loader.py          # CSS loader, font injector, WebRTC style patcher
│   │
│   └── vision/
│       └── exercise_video_processor.py  # WebRTC video processor, pose detection,
│                                          skeleton drawing, form score overlay
│
├── static/
│   ├── style.css                    # Global dark theme styles
│   └── AdobeClean.otf               # Custom font
│
├── .streamlit/
│   └── config.toml                  # Streamlit theme config
│
├── .env                             # Environment variables (not committed)
├── data.db                          # SQLite database (auto-created)
└── requirements.txt                 # Python dependencies
```

---

## How It Works

### Pose Detection Pipeline

Every webcam frame goes through this pipeline:

```
Webcam frame
    → OpenCV flip + color convert
    → MediaPipe PoseLandmarker (VIDEO mode, 33 landmarks)
    → Exercise Detector (angle calculations + rep counting)
    → Form Score (0–100%) + Skeleton Color (green/yellow/red)
    → Overlays drawn on frame
    → Metrics synced to Streamlit session state
```

MediaPipe runs in `VIDEO` mode with incremental timestamps for smooth tracking. The landmarker model detects 33 body landmarks with visibility scores — only landmarks with visibility above 0.7 are used for calculations.

### Form Scoring

Each exercise has a custom scoring function in `workout_config.py`:

- Starts at 100
- Deducts points for specific bad form signals (e.g. sagging hips, too-high squat, excessive back arch)
- Score drives the skeleton color: **green (≥80)**, **yellow (≥50)**, **red (<50)**
- Score badge is rendered directly on the video feed top-right corner

### Rep Counting Logic

All detectors follow the same state machine pattern:

```
angle crosses DOWN threshold  →  stage = "down"
angle crosses UP threshold + stage is "down"  →  stage = "up", reps += 1
```

The detector picks the more visible side (left vs right) using MediaPipe landmark visibility scores.

### Voice Coaching Pipeline

```
sync_metrics_update() called every 0.25s
    → VoicePipeline.process_event(event, exercise, metrics)
    → _find_form_issue() translates raw metrics to plain English
    → Rate limiter: minor events throttled to once every 5 seconds
    → LLMCoach.give_feedback() → Groq API → coaching text (~10-15 words)
    → TextToSpeech.speak() → gTTS → MP3 audio bytes
    → autoplay_audio() → base64 encoded → injected as JS Audio object
```

Voice events in order of priority:

| Event | When It Fires |
|---|---|
| `login` | Once on first login |
| `workout_started` | When Start Workout is clicked |
| `set_completed` | When reps reach the per-set target |
| `workout_completed` | When all sets are finished |
| `no_pose_detected` | When MediaPipe loses the pose |
| `ongoing_form_check` | Every 5 seconds during workout (only if form issue found) |

Pending audio is never overwritten — `ongoing_form_check` is skipped if audio is already queued.

---

## Setup

### Prerequisites

- Python 3.10 or higher
- A webcam
- A Groq API key — get one free at [console.groq.com](https://console.groq.com)
- Internet connection (required for Groq API and gTTS)

### Installation

**1. Clone the repository**

```bash
git clone <your-repo-url>
cd AI-REALTIME-GYM-COACH
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Set up environment variables**

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

**5. Run the app**

```bash
streamlit run main.py
```

---

## Browser Audio Setup

Browsers block programmatic audio autoplay by default. To allow the AI coach voice to play automatically:

**Chrome / Edge**
1. Open the app in your browser
2. Click the lock icon in the address bar
3. Go to Site Settings → Sound → set to **Allow**

**Firefox**
1. Click the lock icon in the address bar
2. Permissions → Autoplay → Allow Audio and Video

This only needs to be done once per browser.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key for LLM inference |

---

## Dependencies

```
streamlit==1.54.0
streamlit-webrtc==0.64.5
mediapipe==0.10.14
opencv-python-headless==4.10.0.84
pandas==2.2.3
groq>=0.12.0
gtts==2.5.3
python-dotenv==1.2.2
```

---

## Key Design Decisions

**Why MediaPipe over a custom model?**
MediaPipe's pose landmarker runs efficiently on CPU, requires no GPU, and provides normalized coordinates with per-landmark visibility scores — making it easy to detect which side of the body is more visible and filter out occluded landmarks.

**Why Groq instead of OpenAI?**
Groq's inference is significantly faster (typically under 1 second for short prompts), which matters for real-time coaching. The `llama-3.3-70b-versatile` model produces natural, conversational coaching language.

**Why gTTS over a paid TTS API?**
gTTS is free and produces natural-sounding speech sufficient for short coaching cues. The tradeoff is it requires internet and has no voice customization — acceptable for this use case.

**Why SQLite?**
Zero-config, no server required, perfect for a single-user local application. The schema is two tables: `users` and `exercises`.

---

## Limitations

- Requires good lighting and a clear background for accurate pose detection
- gTTS requires an active internet connection for every voice cue
- Works best when your full body is visible in the camera frame
- Push-ups and shoulder press work better from a side-on camera angle
- Squats, lunges, and biceps curls work better facing the camera

---

## License

MIT License — free to use, modify, and distribute.
