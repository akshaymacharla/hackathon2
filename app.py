from flask import Flask, request, jsonify, render_template
import uuid, time, random, os
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

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

MURF_API_KEY = os.getenv("MURF_API_KEY", "YOUR_MURF_API_KEY_HERE")

REPEAT_PHRASES = [
    "Blue elephant runs fast",
    "Green banana jumps high",
    "Purple rocket flies slow",
    "Yellow dolphin swims deep",
    "Orange tiger roars loud",
]

STUDENT_LIST = [
    "Rahul Kumar", "Priya Sharma", "Arjun Reddy",
    "Sneha Patel", "Karthik Raj", "Divya Menon",
    "Aditya Singh", "Pooja Nair", "Vikram Rao", "Ananya Das"
]

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def fake_embedding():
    return (np.random.rand(256) * 0.5 + 0.5).tolist()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/teacher")
def teacher():
    return render_template("teacher.html")

@app.route("/student")
def student():
    return render_template("student.html")

@app.route("/api/start-session", methods=["POST"])
def start_session():
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
    student_name = data.get("student_name", "")
    if sid not in sessions:
        return jsonify({"valid": False, "reason": "Invalid session ID"})
    s = sessions[sid]
    if time.time() > s["expiry"]:
        s["active"] = False
        return jsonify({"valid": False, "reason": "Session expired"})
    if student_name in s["disqualified"]:
        return jsonify({"valid": False, "reason": "You are disqualified"})
    return jsonify({"valid": True, "session_id": sid})

@app.route("/api/disqualify", methods=["POST"])
def disqualify():
    data = request.json
    sid = data.get("session_id", "").upper()
    name = data.get("student_name", "")
    if sid in sessions and name:
        sessions[sid]["disqualified"].append(name)
    return jsonify({"disqualified": True})

@app.route("/api/challenge", methods=["GET"])
def get_challenge():
    ctype = random.choice(["math", "math", "repeat", "date"])
    if ctype == "math":
        a = random.randint(5, 20)
        b = random.randint(2, 10)
        op = random.choice(["plus", "minus"])
        answer = str(a + b) if op == "plus" else str(a - b)
        return jsonify({"type": "math", "question": f"What is {a} {op} {b}?", "answer": answer})
    elif ctype == "repeat":
        phrase = random.choice(REPEAT_PHRASES)
        return jsonify({"type": "repeat", "question": f"Repeat after me: {phrase}", "answer": phrase})
    else:
        today = datetime.now().strftime("%B %d %Y")
        return jsonify({"type": "date", "question": "Say today's date", "answer": today})

@app.route("/api/mood", methods=["POST"])
def log_mood():
    data = request.json
    mood = data.get("mood", "").lower()
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in mood_log:
        mood_log[today] = []
    mood_log[today].append(mood)
    return jsonify({"logged": True, "mood": mood})

@app.route("/api/verify", methods=["POST"])
def verify_attendance():
    data = request.json
    name = data.get("name", "").strip()
    spoken_text = data.get("spoken_text", "").lower()
    challenge_answer = data.get("challenge_answer", "").lower()
    challenge_type = data.get("challenge_type", "")
    session_id = data.get("session_id", "").upper()
    today = datetime.now().strftime("%Y-%m-%d")

    if session_id not in sessions:
        return jsonify({"success": False, "reason": "Invalid session"})
    s = sessions[session_id]
    if time.time() > s["expiry"]:
        return jsonify({"success": False, "reason": "Session expired"})
    if name in s["disqualified"]:
        return jsonify({"success": False, "reason": "You are disqualified"})

    matched_name = None
    for sname in STUDENT_LIST:
        if sname.lower() in spoken_text or name.lower() == sname.lower():
            matched_name = sname
            break
    if not matched_name:
        failed_attempts[name] += 1
        return jsonify({"success": False, "reason": "Name not recognized in speech"})

    challenge_passed = False
    if challenge_type == "math":
        challenge_passed = challenge_answer in spoken_text
    elif challenge_type == "repeat":
        expected_words = set(challenge_answer.lower().split())
        spoken_words = set(spoken_text.split())
        overlap = len(expected_words & spoken_words) / len(expected_words)
        challenge_passed = overlap >= 0.6
    elif challenge_type == "date":
        month = datetime.now().strftime("%B").lower()
        day = str(datetime.now().day)
        challenge_passed = month in spoken_text and day in spoken_text

    if not challenge_passed:
        failed_attempts[name] += 1
        if failed_attempts[name] >= 2:
            s["disqualified"].append(name)
            return jsonify({"success": False, "reason": "Too many failed attempts. Suspicious activity detected!", "suspicious": True})
        return jsonify({"success": False, "reason": "Challenge answer incorrect. Try again."})

    current_embedding = fake_embedding()
    similarity = 1.0
    if name in voice_profiles:
        similarity = cosine_similarity(voice_profiles[name], current_embedding)
        if similarity < 0.65:
            failed_attempts[name] += 1
            return jsonify({"success": False, "reason": f"Voice not matched. Are you really {name}?", "suspicious": similarity < 0.60})

    if name not in voice_profiles:
        voice_profiles[name] = current_embedding
    elif similarity > 0.80:
        old = np.array(voice_profiles[name])
        new = np.array(current_embedding)
        voice_profiles[name] = ((old + new) / 2).tolist()

    if today not in attendance:
        attendance[today] = {}
    if name in attendance[today]:
        return jsonify({"success": False, "reason": "Attendance already marked today"})

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if yesterday in attendance and name in attendance[yesterday]:
        streaks[name] = streaks.get(name, 0) + 1
    else:
        streaks[name] = 1

    current_streak = streaks[name]
    leaderboard[name] = leaderboard.get(name, 0) + 1
    attendance[today][name] = {
        "status": "Present",
        "time": datetime.now().strftime("%H:%M:%S"),
        "streak": current_streak,
        "mood": data.get("mood", "unknown")
    }

    parent_alerts[name] = 0
    failed_attempts[name] = 0

    streak_msg = ""
    if current_streak >= 10:
        streak_msg = f" Amazing! This is your {current_streak}th consecutive day. You are on fire!"
    elif current_streak >= 5:
        streak_msg = f" Great job! {current_streak} days in a row!"

    late_msg = ""
    hour = datetime.now().hour
    minute = datetime.now().minute
    if hour > 9 or (hour == 9 and minute > 10):
        late_msg = f" Note: You are {(hour*60+minute)-(9*60+10)} minutes late. Please meet the teacher."

    confirmation = f"{name}, aapki attendance mark ho gayi hai. Your attendance is confirmed!{streak_msg}{late_msg}"

    return jsonify({
        "success": True,
        "name": name,
        "streak": current_streak,
        "similarity": round(similarity, 2),
        "confirmation": confirmation,
        "late": bool(late_msg),
        "leaderboard_rank": sorted(leaderboard, key=leaderboard.get, reverse=True).index(name) + 1
    })

@app.route("/api/teacher-query", methods=["POST"])
def teacher_query():
    data = request.json
    query = data.get("query", "").lower()
    today = datetime.now().strftime("%Y-%m-%d")
    today_att = attendance.get(today, {})
    total = len(STUDENT_LIST)
    present = len(today_att)
    absent_list = [s for s in STUDENT_LIST if s not in today_att]

    if "how many" in query or "count" in query:
        response = f"{present} out of {total} students are present today."
    elif "absent" in query:
        response = f"{len(absent_list)} students are absent: {', '.join(absent_list)}." if absent_list else "All students are present!"
    elif "present" in query:
        present_list = list(today_att.keys())
        response = f"Present: {', '.join(present_list)}." if present_list else "No students present yet."
    elif "mood" in query or "feeling" in query:
        moods = mood_log.get(today, [])
        if moods:
            response = f"Mood report: {moods.count('good')} good, {moods.count('okay')} okay, {moods.count('tired')} tired."
        else:
            response = "No mood data yet today."
    elif "percentage" in query or "rate" in query:
        pct = round((present / total) * 100) if total > 0 else 0
        response = f"Attendance rate is {pct} percent."
    elif "leaderboard" in query or "champion" in query or "top" in query:
        top3 = sorted(leaderboard, key=leaderboard.get, reverse=True)[:3]
        response = f"Champions: {', '.join(top3)}!" if top3 else "No leaderboard data yet."
    else:
        response = f"{present} of {total} present. {len(absent_list)} absent."

    return jsonify({"response": response})

@app.route("/api/mark-absents", methods=["POST"])
def mark_absents():
    today = datetime.now().strftime("%Y-%m-%d")
    today_att = attendance.get(today, {})
    absent_students = [s for s in STUDENT_LIST if s not in today_att]
    alerts = []
    for name in absent_students:
        parent_alerts[name] = parent_alerts.get(name, 0) + 1
        if parent_alerts[name] >= 3:
            alerts.append({
                "name": name,
                "days": parent_alerts[name],
                "message": f"Dear parent, your child {name} has been absent for {parent_alerts[name]} consecutive days. Please contact the college."
            })
        streaks[name] = 0
    return jsonify({"absents": absent_students, "parent_alerts": alerts})

@app.route("/api/weekly-summary", methods=["GET"])
def weekly_summary():
    total = len(STUDENT_LIST)
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
    summary = f"Last week the class had {avg} percent average attendance. {best_day['day']} was highest, {worst_day['day']} was lowest."
    if top3:
        summary += f" Champions: {', '.join(top3)}."
    return jsonify({"summary": summary, "days": days, "average": avg})

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    ranked = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
    return jsonify({"leaderboard": [{"name": n, "days": d, "streak": streaks.get(n, 0)} for n, d in ranked]})

@app.route("/api/speak", methods=["POST"])
def speak():
    import requests as req
    data = request.json
    text = data.get("text", "")
    try:
        resp = req.post(
            "https://api.murf.ai/v1/speech/generate",
            headers={"api-key": MURF_API_KEY, "Content-Type": "application/json"},
            json={"voiceId": "en-IN-aarav", "text": text, "modelVersion": "GEN2", "format": "MP3"},
            timeout=10
        )
        result = resp.json()
        return jsonify({"audio_url": result.get("audioFile", ""), "text": text})
    except Exception as e:
        return jsonify({"error": str(e), "text": text}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')