# VoxAttend — AI Powered Voice Smart Attendance System 🎙️✨

> **Proxy-proof · Voice-first · AI-powered**

VoxAttend is a cutting-edge, voice-first attendance system designed to eliminate proxy attendance in modern classrooms. By combining **Murf AI’s** high-fidelity voice synthesis with real-time browser focus detection and voice verification, VoxAttend ensures that every attendance entry is authentic and verified.

---

## 🚀 Features

### 👨‍🏫 Teacher Workflow
- **One-Click Session**: Instantly generate a dynamic attendance QR code.
- **Voice Query Dashboard**: Use natural language to ask "Who is absent?" or "Show leaderboard."
- **Live Stats**: Real-time tracking of present/absent counts and rates.
- **Parent Alerts**: Automatic flagging and report generation for frequent absentees.

### 👨‍🎓 Student Workflow
- **Zero App Install**: Web-based scanning and verification via browser.
- **Voice Challenge**: Dynamic phrases that must be spoken to confirm presence.
- **Gamified Progress**: Tracking attendance streaks and mood reports.

---

## 🧠 How it Works (API Usage)

VoxAttend relies on a robust set of APIs to ensure security and accessibility.

### 🎙️ Murf AI API
VoxAttend uses the **Murf AI Text-to-Speech API** to provide high-quality, natural system instructions and feedback.

- **Endpoint**: `POST /api/speak`
- **Request Format**:
  ```json
  {
    "text": "Welcome to VoxAttend. Please scan the QR code to begin."
  }
  ```
- **Response**: MP3/WAV Audio Stream (or cached URL).

**Usage in VoxAttend:**
1. **Instructional Voice**: Guides students through the scanning and recording process.
2. **Instant Feedback**: Provides immediate voice confirmation for success or failure ("Verification Successful," "Access Denied").
3. **Teacher Queries**: Reads out attendance summaries and mood reports to teachers.

### 🧱 Core Endpoints
- `/api/start-session`: Generates a new unique `session_id` and starts the 60s timer.
- `/api/validate-session`: Checks if a scanned `session_id` is still active and valid.
- `/api/challenge`: Provides a unique voice phrase for the student to repeat.
- `/api/verify`: Analyzes uploaded audio against the student's voice profile using Resemblyzer.

---

## 🔒 Security & Privacy
Security is built into the architecture of VoxAttend:
- **Environment Variables**: Sensitive credentials like `MURF_API_KEY` and `TEACHER_PASSWORD` are stored in a `.env` file.
- **Git Protection**: The `.env` file is explicitly excluded from version control via `.gitignore` to prevent accidental credential leakage.
- **Anti-Proxy Logic**: Browser focus detection terminates sessions if a student attempts to minimize the window or switch tabs.

---

## 🎥 Demo Video
[https://youtu.be/WGYfHxxEAAs?si=C2yFEFonlpdrkw7S](#)

---

## 🛠️ Tech Stack
- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3 (Modern Glassmorphism), Vanilla JavaScript
- **Voice Synthesis**: Murf AI (TTS)
- **Voice Recognition**: Web Speech API (STT) & MediaRecorder API
- **Data Analysis**: NumPy & Resemblyzer (Voice Similarity)

---

## ⚙️ Setup Instructions

### 1. Clone the Repo
```bash
git clone https://github.com/akshaymacharla/hackathon3.git
cd voice-attendance
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the root directory:
```env
MURF_API_KEY=your_murf_api_key_here
TEACHER_PASSWORD=teacher123
```

### 4. Run the App
```bash
python app.py
```
Open `http://127.0.0.1:10000` to access the portal.

---

## ⚠️ Important Note
This project leverages **Murf AI** for generating natural, premium voice responses. A valid API key is required in the environment variables for full functionality.

---
Built with ❤️ for the Hackathon. 🎙️
