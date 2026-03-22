student = open('templates/student.html', 'w', encoding='utf-8')
student.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Student Attendance</title>
<link rel="stylesheet" href="/static/css/style.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"></script>
</head>
<body>
<div class="disqualify-overlay hidden" id="disqualify-overlay">
  <div class="disqualify-box">
    <div class="disqualify-icon">🚫</div>
    <h2>Session Terminated</h2>
    <p>You left the attendance page. You are disqualified.</p>
  </div>
</div>
<div class="container" id="main-content">
  <header>
    <a href="/" class="back-btn" id="back-btn">Home</a>
    <h1>Mark Attendance</h1>
    <div class="focus-warning">Do not leave this page!</div>
  </header>
  <div class="step-panel active" id="step-qr">
    <div class="step-header"><div class="step-badge">Step 1</div><h2>Scan QR Code</h2></div>
    <p class="hint">Point your camera at the QR code on the projector</p>
    <div id="qr-reader" class="qr-reader-box"></div>
    <div class="divider">or enter manually</div>
    <div class="manual-entry">
      <input type="text" id="manual-session" placeholder="Enter Session ID" maxlength="8"/>
      <button class="btn btn-primary" onclick="validateManualSession()">Enter</button>
    </div>
    <div id="qr-status" class="status-msg"></div>
  </div>
  <div class="step-panel hidden" id="step-mood">
    <div class="step-header"><div class="step-badge">Step 2</div><h2>How are you feeling today?</h2></div>
    <div id="mood-voice-prompt" class="voice-prompt-box">How are you feeling today?</div>
    <div class="mood-buttons">
      <button class="mood-btn" onclick="selectMood('good')">😊 Good</button>
      <button class="mood-btn" onclick="selectMood('okay')">😐 Okay</button>
      <button class="mood-btn" onclick="selectMood('tired')">😴 Tired</button>
    </div>
  </div>
  <div class="step-panel hidden" id="step-challenge">
    <div class="step-header"><div class="step-badge">Step 3</div><h2>Live Challenge</h2></div>
    <p class="hint">Read the question and answer it out loud</p>
    <div class="challenge-box">
      <div class="challenge-icon">🎯</div>
      <div class="challenge-text" id="challenge-text">Loading challenge...</div>
    </div>
    <button class="btn btn-primary btn-large" onclick="goToVerify()">I am Ready to Answer</button>
  </div>
  <div class="step-panel hidden" id="step-verify">
    <div class="step-header"><div class="step-badge">Step 4</div><h2>Voice Verification</h2></div>
    <div class="name-row">
      <input type="text" id="student-name" placeholder="Your full name" list="student-names"/>
      <datalist id="student-names"></datalist>
    </div>
    <div class="instruction-box">
      <p>Say exactly:</p>
      <div class="say-this" id="say-this-text">Loading...</div>
    </div>
    <div class="record-section">
      <button class="btn btn-mic btn-large" id="record-btn" onclick="startRecording()">🎤 Start Recording</button>
      <div class="record-status hidden" id="record-status">
        <div class="pulse-ring"></div>
        <span>Recording... speak now</span>
      </div>
      <div class="transcript-box" id="transcript-box">Your words will appear here...</div>
    </div>
    <button class="btn btn-primary btn-large hidden" id="verify-btn" onclick="verifyAttendance()">✅ Verify Attendance</button>
    <div class="processing hidden" id="processing">
      <div class="spinner"></div>
      <span>Processing your voice...</span>
    </div>
  </div>
  <div class="step-panel hidden" id="step-result">
    <div id="result-success" class="hidden">
      <div class="result-icon">✅</div>
      <h2 id="result-name"></h2>
      <div class="result-details">
        <div class="result-badge" id="streak-badge"></div>
        <div class="result-badge" id="rank-badge"></div>
        <div class="result-badge late-badge hidden" id="late-badge"></div>
      </div>
      <div class="confirmation-text" id="confirmation-text"></div>
    </div>
    <div id="result-fail" class="hidden">
      <div class="result-icon">❌</div>
      <h2>Verification Failed</h2>
      <p id="fail-reason"></p>
      <button class="btn btn-primary" onclick="retryVerify()">🔄 Try Again</button>
    </div>
    <div id="result-suspicious" class="hidden">
      <div class="result-icon">⚠️</div>
      <h2>Suspicious Activity</h2>
      <p>Too many failed attempts. Session locked.</p>
    </div>
  </div>
</div>
<script src="/static/js/murf.js"></script>
<script>
let sessionId = null;
let studentMood = "unknown";
let challenge = null;
let isSessionActive = false;
let mediaRecorder = null;
let audioChunks = [];
let spokenText = "";
let audioBlob = null;
let isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);

document.addEventListener("visibilitychange", () => {
  if (isSessionActive && document.hidden && !isMobile) {
    disqualify();
  }
});

async function disqualify() {
  if (!isSessionActive) return;
  isSessionActive = false;
  const name = document.getElementById("student-name").value || "";
  if (sessionId) {
    await fetch("/api/disqualify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, student_name: name })
    });
  }
  document.getElementById("disqualify-overlay").classList.remove("hidden");
  document.getElementById("main-content").style.opacity = "0.2";
  document.getElementById("main-content").style.pointerEvents = "none";
}

async function loadStudentNames() {
  try {
    const res = await fetch("/api/student-list");
    const data = await res.json();
    const datalist = document.getElementById("student-names");
    datalist.innerHTML = data.students.map(s =>
      "<option value='" + s.name + "'>"
    ).join("");
  } catch(e) {}
}

window.onload = () => {
  loadStudentNames();
  try {
    const html5QrCode = new Html5Qrcode("qr-reader");
    html5QrCode.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 220, height: 220 } },
      (decodedText) => {
        html5QrCode.stop();
        handleScannedSession(decodedText.trim().toUpperCase());
      },
      () => {}
    ).catch(() => {
      document.getElementById("qr-status").textContent = "Camera not available. Use manual entry below.";
    });
  } catch(e) {
    document.getElementById("qr-status").textContent = "Camera not available. Use manual entry below.";
  }
};

async function handleScannedSession(sid) {
  document.getElementById("qr-status").textContent = "Validating session...";
  try {
    const res = await fetch("/api/validate-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sid, student_name: "" })
    });
    const data = await res.json();
    if (data.valid) {
      sessionId = sid;
      isSessionActive = true;
      document.getElementById("back-btn").onclick = (e) => e.preventDefault();
      showStep("step-mood");
    } else {
      document.getElementById("qr-status").textContent = "❌ " + data.reason;
    }
  } catch(e) {
    document.getElementById("qr-status").textContent = "Error validating session. Try manual entry.";
  }
}

function validateManualSession() {
  const sid = document.getElementById("manual-session").value.trim().toUpperCase();
  if (sid.length < 4) return;
  handleScannedSession(sid);
}

async function selectMood(mood) {
  studentMood = mood;
  try {
    await fetch("/api/mood", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mood })
    });
  } catch(e) {}
  await loadChallenge();
  showStep("step-challenge");
}

async function loadChallenge() {
  try {
    const res = await fetch("/api/challenge");
    challenge = await res.json();
    document.getElementById("challenge-text").textContent = challenge.question;
  } catch(e) {
    challenge = { type: "math", question: "What is 5 plus 3?", answer: "8" };
    document.getElementById("challenge-text").textContent = challenge.question;
  }
}

function goToVerify() {
  document.getElementById("say-this-text").textContent =
    "I am [Your Name]. " + (challenge.type === "repeat" ? challenge.answer : "The answer is " + challenge.answer);
  showStep("step-verify");
}

async function startRecording() {
  const name = document.getElementById("student-name").value.trim();
  if (!name) {
    alert("Please enter your name first!");
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Microphone not supported! Please use Chrome browser.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    document.getElementById("record-btn").textContent = "🔴 Recording... (5 sec)";
    document.getElementById("record-status").classList.remove("hidden");
    document.getElementById("transcript-box").textContent = "Listening...";

    if (window.SpeechRecognition || window.webkitSpeechRecognition) {
      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
      recognition.lang = "en-IN";
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.onresult = (e) => {
        spokenText = e.results[0][0].transcript;
        document.getElementById("transcript-box").textContent = '"' + spokenText + '"';
      };
      recognition.onerror = () => {
        spokenText = name + " the answer is " + (challenge ? challenge.answer : "");
        document.getElementById("transcript-box").textContent = "Using name match only.";
      };
      try { recognition.start(); } catch(e) {
        spokenText = name + " the answer is " + (challenge ? challenge.answer : "");
      }
    } else {
      spokenText = name + " the answer is " + (challenge ? challenge.answer : "");
      document.getElementById("transcript-box").textContent = "Speech recognition not available. Using name match.";
    }

    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };
    mediaRecorder.onstop = () => {
      audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      stream.getTracks().forEach(track => track.stop());
      document.getElementById("verify-btn").classList.remove("hidden");
      document.getElementById("record-status").classList.add("hidden");
      document.getElementById("record-btn").textContent = "🎤 Record Again";
      document.getElementById("record-btn").onclick = startRecording;
    };

    mediaRecorder.start();
    document.getElementById("record-btn").onclick = stopRecording;

    setTimeout(() => {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        stopRecording();
      }
    }, 5000);

  } catch(err) {
    if (err.name === "NotAllowedError") {
      alert("Microphone blocked!\\n\\nPlease:\\n1. Click lock icon in address bar\\n2. Set Microphone to Allow\\n3. Refresh the page");
    } else if (err.name === "NotFoundError") {
      alert("No microphone found!");
    } else {
      alert("Microphone error: " + err.message);
    }
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

async function verifyAttendance() {
  const name = document.getElementById("student-name").value.trim();
  if (!name) { alert("Please enter your name."); return; }
  if (!spokenText) {
    spokenText = name + " the answer is " + (challenge ? challenge.answer : "");
  }

  document.getElementById("processing").classList.remove("hidden");
  document.getElementById("verify-btn").disabled = true;

  let audioB64 = "";
  if (audioBlob) {
    try {
      const buf = await audioBlob.arrayBuffer();
      audioB64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
    } catch(e) {}
  }

  try {
    const res = await fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name, spoken_text: spokenText,
        challenge_answer: challenge ? challenge.answer : "",
        challenge_type: challenge ? challenge.type : "math",
        session_id: sessionId, mood: studentMood, audio: audioB64
      })
    });
    const data = await res.json();
    document.getElementById("processing").classList.add("hidden");
    showStep("step-result");

    if (data.success) {
      document.getElementById("result-success").classList.remove("hidden");
      document.getElementById("result-fail").classList.add("hidden");
      document.getElementById("result-suspicious").classList.add("hidden");
      document.getElementById("result-name").textContent = "✅ " + data.name;
      document.getElementById("streak-badge").textContent = "🔥 " + data.streak + " day streak";
      document.getElementById("rank-badge").textContent = "🏆 Rank #" + data.leaderboard_rank;
      document.getElementById("confirmation-text").textContent = data.confirmation;
      if (data.late) {
        document.getElementById("late-badge").classList.remove("hidden");
        document.getElementById("late-badge").textContent = "⏰ Late arrival";
      }
    } else if (data.suspicious) {
      document.getElementById("result-suspicious").classList.remove("hidden");
      document.getElementById("result-success").classList.add("hidden");
      document.getElementById("result-fail").classList.add("hidden");
    } else {
      document.getElementById("result-fail").classList.remove("hidden");
      document.getElementById("result-success").classList.add("hidden");
      document.getElementById("result-suspicious").classList.add("hidden");
      document.getElementById("fail-reason").textContent = data.reason;
    }
  } catch(e) {
    document.getElementById("processing").classList.add("hidden");
    document.getElementById("verify-btn").disabled = false;
    alert("Error verifying attendance. Please try again.");
  }
}

function retryVerify() {
  spokenText = "";
  audioBlob = null;
  document.getElementById("transcript-box").textContent = "Your words will appear here...";
  document.getElementById("verify-btn").classList.add("hidden");
  document.getElementById("verify-btn").disabled = false;
  showStep("step-verify");
}

function showStep(stepId) {
  document.querySelectorAll(".step-panel").forEach(p => p.classList.add("hidden"));
  document.getElementById(stepId).classList.remove("hidden");
}
</script>
</body>
</html>""")
student.close()
print("student.html fixed!")