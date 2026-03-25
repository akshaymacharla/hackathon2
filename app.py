from flask import Flask, request, jsonify, render_template, session, redirect
import uuid, time, random, os
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import requests as req
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = "voice_attendance_secret_2024"

sessions = {}
attendance = {}
voice_profiles = {}
streaks = {}
leaderboard = {}
mood_log = {}
failed_attempts = defaultdict(int)
parent_alerts = {}
TTS_CACHE = {}  # {text: audio_url}

# Student list — roll_no → name
STUDENT_REGISTRY = {}  # {"CS001": "Rahul Kumar", "CS002": "Priya Sharma"}

MURF_API_KEY = os.getenv("MURF_API_KEY", "YOUR_MURF_API_KEY_HERE")
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "teacher123")

REPEAT_PHRASES = [
    "Blue elephant runs fast",
    "Green banana jumps high",
    "Purple rocket flies slow",
    "Yellow dolphin swims deep",
    "Orange tiger roars loud",
]

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def fake_embedding():
    return (np.random.rand(256) * 0.5 + 0.5).tolist()

# ── Pages ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/teacher")
def teacher():
    if not session.get("is_teacher"):
        return redirect("/teacher-login")
    return render_template("teacher.html")

@app.route("/teacher-login")
def teacher_login():
    return render_template("teacher_login.html")

@app.route("/student")
def student():
    return render_template("student.html")

# ── Teacher Auth ───────────────────────────────────────────────────
@app.route("/api/teacher-login", methods=["POST"])
def do_teacher_login():
    data = request.json
    password = data.get("password", "")
    if password == TEACHER_PASSWORD:
        session["is_teacher"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "reason": "Wrong password!"})

@app.route("/api/teacher-logout", methods=["POST"])
def teacher_logout():
    session.pop("is_teacher", None)
    return jsonify({"success": True})

# ── Student Registration (Teacher Only) ───────────────────────────
@app.route("/api/register-student", methods=["POST"])
def register_student():
    if not session.get("is_teacher"):
        return jsonify({"success": False, "reason": "Only teacher can register students!"})
    data = request.json
    roll_no = data.get("roll_no", "").strip().upper()
    name = data.get("name", "").strip()
    if not roll_no or not name:
        return jsonify({"success": False, "reason": "Roll number and name required!"})
    STUDENT_REGISTRY[roll_no] = name
    voice_profiles[roll_no] = fake_embedding()
    return jsonify({"success": True, "message": name + " (" + roll_no + ") registered!"})

@app.route("/api/student-list", methods=["GET"])
def student_list():
    students = [{"roll_no": k, "name": v, "has_voice": k in voice_profiles} for k, v in STUDENT_REGISTRY.items()]
    return jsonify({"students": students})

@app.route("/api/delete-student", methods=["POST"])
def delete_student():
    if not session.get("is_teacher"):
        return jsonify({"success": False, "reason": "Only teacher can delete students!"})
    data = request.json
    roll_no = data.get("roll_no", "").strip().upper()
    if roll_no in STUDENT_REGISTRY:
        del STUDENT_REGISTRY[roll_no]
    if roll_no in voice_profiles:
        del voice_profiles[roll_no]
    return jsonify({"success": True})

# ── Session Management ─────────────────────────────────────────────
@app.route("/api/start-session", methods=["POST"])
def start_session():
    if not session.get("is_teacher"):
        return jsonify({"success": False, "reason": "Only teacher can start sessions!"})
    session_id = str(uuid.uuid4())[:8].upper()
    expiry = time.time() + 60
    sessions[session_id] = {
        "expiry": expiry,
        "active": True,
        "disqualified": [],
        "created_at": datetime.now().isoformat()
    }
    return jsonify({"session_id": session_id, "expiry": expiry, "expires_in": 60})

@app.route("/api/validate-session", methods=["POST"])
def validate_session():
    data = request.json
    sid = data.get("session_id", "").strip().upper()
    roll_no = data.get("roll_no", "").strip().upper()
    if sid not in sessions:
        return jsonify({"valid": False, "reason": "Invalid session ID"})
    s = sessions[sid]
    if time.time() > s["expiry"]:
        s["active"] = False
        return jsonify({"valid": False, "reason": "Session expired! Ask teacher for new QR."})
    if roll_no and roll_no in s["disqualified"]:
        return jsonify({"valid": False, "reason": "You are disqualified from this session!"})
    return jsonify({"valid": True, "session_id": sid})

@app.route("/api/disqualify", methods=["POST"])
def disqualify():
    data = request.json
    sid = data.get("session_id", "").upper()
    roll_no = data.get("roll_no", "").upper()
    if sid in sessions and roll_no:
        sessions[sid]["disqualified"].append(roll_no)
    return jsonify({"disqualified": True})

# ── Challenge ──────────────────────────────────────────────────────
@app.route("/api/challenge", methods=["GET"])
def get_challenge():
    ctype = random.choice(["math", "math", "repeat", "date"])
    if ctype == "math":
        a = random.randint(5, 20)
        b = random.randint(2, 10)
        op = random.choice(["plus", "minus"])
        answer = str(a + b) if op == "plus" else str(a - b)
        return jsonify({"type": "math", "question": "What is " + str(a) + " " + op + " " + str(b) + "?", "answer": answer})
    elif ctype == "repeat":
        phrase = random.choice(REPEAT_PHRASES)
        return jsonify({"type": "repeat", "question": "Repeat after me: " + phrase, "answer": phrase})
    else:
        today = datetime.now().strftime("%B %d %Y")
        return jsonify({"type": "date", "question": "Say today's date", "answer": today})

# ── Mood ───────────────────────────────────────────────────────────
@app.route("/api/mood", methods=["POST"])
def log_mood():
    data = request.json
    mood = data.get("mood", "").lower()
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in mood_log:
        mood_log[today] = []
    mood_log[today].append(mood)
    return jsonify({"logged": True, "mood": mood})

# ── Verify Attendance ──────────────────────────────────────────────
@app.route("/api/verify", methods=["POST"])
def verify_attendance():
    data = request.json
    roll_no = data.get("roll_no", "").strip().upper()
    name = data.get("name", "").strip()
    spoken_text = data.get("spoken_text", "").lower()
    challenge_answer = data.get("challenge_answer", "").lower()
    challenge_type = data.get("challenge_type", "")
    session_id = data.get("session_id", "").upper()
    today = datetime.now().strftime("%Y-%m-%d")

    if session_id not in sessions:
        return jsonify({"success": False, "reason": "Invalid session!"})
    s = sessions[session_id]
    if time.time() > s["expiry"]:
        return jsonify({"success": False, "reason": "Session expired!"})
    if roll_no in s["disqualified"]:
        return jsonify({"success": False, "reason": "You are disqualified!"})

    # Check if roll number is registered
    if roll_no not in STUDENT_REGISTRY:
        return jsonify({"success": False, "reason": "Roll number " + roll_no + " not registered! Contact your teacher."})

    # Get student name from registry
    registered_name = STUDENT_REGISTRY[roll_no]

    # Challenge check
    challenge_passed = False
    if challenge_type == "math":
        challenge_passed = challenge_answer in spoken_text
    elif challenge_type == "repeat":
        expected_words = set(challenge_answer.lower().split())
        spoken_words = set(spoken_text.split())
        overlap = len(expected_words & spoken_words) / len(expected_words) if expected_words else 0
        challenge_passed = overlap >= 0.6
    elif challenge_type == "date":
        month = datetime.now().strftime("%B").lower()
        day = str(datetime.now().day)
        challenge_passed = month in spoken_text and day in spoken_text
    else:
        challenge_passed = True

    if not challenge_passed:
        failed_attempts[roll_no] += 1
        if failed_attempts[roll_no] >= 2:
            s["disqualified"].append(roll_no)
            return jsonify({"success": False, "reason": "Too many failed attempts! Suspicious activity.", "suspicious": True})
        return jsonify({"success": False, "reason": "Wrong answer! Try again."})

    # Voice check
    current_embedding = fake_embedding()
    similarity = 1.0
    if roll_no in voice_profiles:
        similarity = cosine_similarity(voice_profiles[roll_no], current_embedding)
        if similarity > 0.80:
            old = np.array(voice_profiles[roll_no])
            new = np.array(current_embedding)
            voice_profiles[roll_no] = ((old + new) / 2).tolist()

    if today not in attendance:
        attendance[today] = {}
    if roll_no in attendance[today]:
        return jsonify({"success": False, "reason": "Attendance already marked today!"})

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if yesterday in attendance and roll_no in attendance[yesterday]:
        streaks[roll_no] = streaks.get(roll_no, 0) + 1
    else:
        streaks[roll_no] = 1

    current_streak = streaks[roll_no]
    leaderboard[roll_no] = leaderboard.get(roll_no, 0) + 1
    attendance[today][roll_no] = {
        "name": registered_name,
        "status": "Present",
        "time": datetime.now().strftime("%H:%M:%S"),
        "streak": current_streak,
        "mood": data.get("mood", "unknown")
    }

    parent_alerts[roll_no] = 0
    failed_attempts[roll_no] = 0

    streak_msg = ""
    if current_streak >= 10:
        streak_msg = " Amazing! " + str(current_streak) + " days in a row! You are on fire!"
    elif current_streak >= 5:
        streak_msg = " Great job! " + str(current_streak) + " days in a row!"

    late_msg = ""
    hour = datetime.now().hour
    minute = datetime.now().minute
    if hour > 9 or (hour == 9 and minute > 10):
        late_msg = " Note: You are " + str((hour*60+minute)-(9*60+10)) + " minutes late."

    confirmation = registered_name + ", aapki attendance mark ho gayi hai. Your attendance is confirmed!" + streak_msg + late_msg

    ranked = sorted(leaderboard, key=leaderboard.get, reverse=True)
    rank = ranked.index(roll_no) + 1 if roll_no in ranked else 1

    return jsonify({
        "success": True,
        "name": registered_name,
        "roll_no": roll_no,
        "streak": current_streak,
        "confirmation": confirmation,
        "late": bool(late_msg),
        "leaderboard_rank": rank
    })

# ── Teacher Queries ────────────────────────────────────────────────
@app.route("/api/teacher-query", methods=["POST"])
def teacher_query():
    data = request.json
    query = data.get("query", "").lower()
    today = datetime.now().strftime("%Y-%m-%d")
    today_att = attendance.get(today, {})
    total = len(STUDENT_REGISTRY)
    present = len(today_att)
    absent_list = [STUDENT_REGISTRY[r] + " (" + r + ")" for r in STUDENT_REGISTRY if r not in today_att]

    if "how many" in query or "count" in query:
        response = str(present) + " out of " + str(total) + " students are present today."
    elif "absent" in query:
        response = str(len(absent_list)) + " students are absent: " + ", ".join(absent_list) + "." if absent_list else "All students are present!"
    elif "present" in query:
        present_list = [attendance[today][r]["name"] + " (" + r + ")" for r in today_att]
        response = "Present: " + ", ".join(present_list) + "." if present_list else "No students present yet."
    elif "mood" in query:
        moods = mood_log.get(today, [])
        if moods:
            response = "Mood report: " + str(moods.count("good")) + " good, " + str(moods.count("okay")) + " okay, " + str(moods.count("tired")) + " tired."
        else:
            response = "No mood data yet today."
    elif "percentage" in query or "rate" in query:
        pct = round((present / total) * 100) if total > 0 else 0
        response = "Attendance rate is " + str(pct) + " percent."
    elif "leaderboard" in query or "champion" in query:
        top3 = sorted(leaderboard, key=leaderboard.get, reverse=True)[:3]
        names = [STUDENT_REGISTRY.get(r, r) for r in top3]
        response = "Champions: " + ", ".join(names) + "!" if names else "No leaderboard data yet."
    else:
        response = str(present) + " of " + str(total) + " present. " + str(len(absent_list)) + " absent."

    return jsonify({"response": response})

@app.route("/api/mark-absents", methods=["POST"])
def mark_absents():
    today = datetime.now().strftime("%Y-%m-%d")
    today_att = attendance.get(today, {})
    absent_rolls = [r for r in STUDENT_REGISTRY if r not in today_att]
    alerts = []
    for roll_no in absent_rolls:
        parent_alerts[roll_no] = parent_alerts.get(roll_no, 0) + 1
        if parent_alerts[roll_no] >= 3:
            name = STUDENT_REGISTRY.get(roll_no, roll_no)
            alerts.append({
                "name": name,
                "roll_no": roll_no,
                "days": parent_alerts[roll_no],
                "message": "Dear parent, your child " + name + " has been absent for " + str(parent_alerts[roll_no]) + " consecutive days."
            })
        streaks[roll_no] = 0
    absent_names = [STUDENT_REGISTRY.get(r, r) for r in absent_rolls]
    return jsonify({"absents": absent_names, "parent_alerts": alerts})

@app.route("/api/weekly-summary", methods=["GET"])
def weekly_summary():
    total = len(STUDENT_REGISTRY)
    days = []
    total_pct = 0
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_name = (datetime.now() - timedelta(days=i)).strftime("%A")
        count = len(attendance.get(day, {}))
        pct = round((count / total) * 100) if total > 0 else 0
        days.append({"day": day_name, "present": count, "percentage": pct})
        total_pct += pct
    avg = round(total_pct / 7)
    best_day = max(days, key=lambda x: x["percentage"])
    worst_day = min(days, key=lambda x: x["percentage"])
    top3 = sorted(leaderboard, key=leaderboard.get, reverse=True)[:3]
    names = [STUDENT_REGISTRY.get(r, r) for r in top3]
    summary = "Last week the class had " + str(avg) + " percent average attendance. " + best_day["day"] + " was highest, " + worst_day["day"] + " was lowest."
    if names:
        summary += " Champions: " + ", ".join(names) + "."
    return jsonify({"summary": summary, "days": days, "average": avg})

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    ranked = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
    return jsonify({"leaderboard": [{"roll_no": r, "name": STUDENT_REGISTRY.get(r, r), "days": d, "streak": streaks.get(r, 0)} for r, d in ranked]})

@app.route("/api/speak", methods=["POST"])
def speak():
    data = request.json
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    # Check cache
    if text in TTS_CACHE:
        return jsonify({"audio_url": TTS_CACHE[text], "text": text, "cached": True})

    if not MURF_API_KEY or MURF_API_KEY == "YOUR_MURF_API_KEY_HERE":
        return jsonify({"error": "Murf API Key not configured", "text": text}), 500

    try:
        resp = req.post(
            "https://api.murf.ai/v1/speech/generate",
            headers={"api-key": MURF_API_KEY, "Content-Type": "application/json"},
            json={
                "voiceId": "en-IN-aarav", 
                "text": text, 
                "modelVersion": "GEN2", 
                "format": "MP3"
            },
            timeout=10
        )
        resp.raise_for_status()
        result = resp.json()
        audio_url = result.get("audioFile", "")
        if audio_url:
            TTS_CACHE[text] = audio_url
        return jsonify({"audio_url": audio_url, "text": text})
    except Exception as e:
        return jsonify({"error": str(e), "text": text}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host="0.0.0.0", port=port)