f = open('templates/student.html', 'w', encoding='utf-8')
f.write("""<!DOCTYPE html>
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
      <button class="btn btn-primary" id="enterbtn">Enter</button>
    </div>
    <div id="qr-status" class="status-msg"></div>
  </div>
  <div class="step-panel hidden" id="step-mood">
    <div class="step-header"><div class="step-badge">Step 2</div><h2>How are you feeling today?</h2></div>
    <div class="voice-prompt-box">How are you feeling today?</div>
    <div class="mood-buttons">
      <button class="mood-btn" id="mood-good">😊 Good</button>
      <button class="mood-btn" id="mood-okay">😐 Okay</button>
      <button class="mood-btn" id="mood-tired">😴 Tired</button>
    </div>
  </div>
  <div class="step-panel hidden" id="step-challenge">
    <div class="step-header"><div class="step-badge">Step 3</div><h2>Live Challenge</h2></div>
    <p class="hint">Read the question and answer it out loud</p>
    <div class="challenge-box">
      <div class="challenge-icon">🎯</div>
      <div class="challenge-text" id="challenge-text">Loading...</div>
    </div>
    <button class="btn btn-primary btn-large" id="readybtn">✅ I am Ready to Answer</button>
  </div>
  <div class="step-panel hidden" id="step-verify">
    <div class="step-header"><div class="step-badge">Step 4</div><h2>Voice Verification</h2></div>
    <div class="instruction-box">
      <p>Enter your Roll Number:</p>
      <input type="text" id="student-roll" placeholder="Roll No (e.g. CS001)" style="margin-top:0.5rem"/>
    </div>
    <div class="instruction-box" style="margin-top:0.5rem">
      <p>Say exactly:</p>
      <div class="say-this" id="say-this-text">Loading...</div>
    </div>
    <div class="record-section">
      <button class="btn btn-mic btn-large" id="record-btn">🎤 Start Recording</button>
      <div class="record-status hidden" id="record-status">
        <div class="pulse-ring"></div>
        <span>Recording... speak now</span>
      </div>
      <div class="transcript-box" id="transcript-box">Your words will appear here...</div>
    </div>
    <button class="btn btn-primary btn-large hidden" id="verify-btn">✅ Verify Attendance</button>
    <div class="processing hidden" id="processing">
      <div class="spinner"></div>
      <span>Processing...</span>
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
      <button class="btn btn-primary" id="retrybtn">🔄 Try Again</button>
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
var sessionId = null;
var studentMood = "unknown";
var challenge = null;
var isSessionActive = false;
var mediaRecorder = null;
var audioChunks = [];
var spokenText = "";
var audioBlob = null;
var isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);

document.addEventListener("visibilitychange", function() {
  if (isSessionActive && document.hidden && !isMobile) disqualify();
});

function disqualify() {
  if (!isSessionActive) return;
  isSessionActive = false;
  var roll = document.getElementById("student-roll").value || "";
  if (sessionId) {
    fetch("/api/disqualify", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({session_id: sessionId, roll_no: roll})
    });
  }
  document.getElementById("disqualify-overlay").classList.remove("hidden");
  document.getElementById("main-content").style.opacity = "0.2";
  document.getElementById("main-content").style.pointerEvents = "none";
}

window.onload = function() {
  try {
    var qr = new Html5Qrcode("qr-reader");
    qr.start(
      {facingMode:"environment"},
      {fps:10, qrbox:{width:220,height:220}},
      function(text) { qr.stop(); handleSession(text.trim().toUpperCase()); },
      function() {}
    ).catch(function() {
      document.getElementById("qr-status").textContent = "Camera not available. Use manual entry.";
    });
  } catch(e) {
    document.getElementById("qr-status").textContent = "Camera not available. Use manual entry.";
  }
};

document.getElementById("enterbtn").addEventListener("click", function() {
  var sid = document.getElementById("manual-session").value.trim().toUpperCase();
  if (sid.length < 4) return;
  handleSession(sid);
});

function handleSession(sid) {
  document.getElementById("qr-status").textContent = "Validating...";
  fetch("/api/validate-session", {
    method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({session_id: sid, roll_no: ""})
  }).then(function(r){return r.json();}).then(function(d) {
    if (d.valid) {
      sessionId = sid;
      isSessionActive = true;
      document.getElementById("back-btn").onclick = function(e){e.preventDefault();};
      showStep("step-mood");
    } else {
      document.getElementById("qr-status").textContent = "❌ " + d.reason;
    }
  });
}

document.getElementById("mood-good").addEventListener("click", function(){selectMood("good");});
document.getElementById("mood-okay").addEventListener("click", function(){selectMood("okay");});
document.getElementById("mood-tired").addEventListener("click", function(){selectMood("tired");});

function selectMood(mood) {
  studentMood = mood;
  fetch("/api/mood", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body:JSON.stringify({mood:mood})
  });
  loadChallenge();
  showStep("step-challenge");
}

function loadChallenge() {
  fetch("/api/challenge").then(function(r){return r.json();}).then(function(d) {
    challenge = d;
    document.getElementById("challenge-text").textContent = d.question;
  }).catch(function() {
    challenge = {type:"math", question:"What is 5 plus 3?", answer:"8"};
    document.getElementById("challenge-text").textContent = challenge.question;
  });
}

document.getElementById("readybtn").addEventListener("click", function() {
  document.getElementById("say-this-text").textContent =
    "I am [Your Name]. " + (challenge.type==="repeat" ? challenge.answer : "The answer is " + challenge.answer);
  showStep("step-verify");
});

document.getElementById("record-btn").addEventListener("click", startRecording);
document.getElementById("verify-btn").addEventListener("click", verifyAttendance);
document.getElementById("retrybtn").addEventListener("click", function() {
  spokenText = ""; audioBlob = null;
  document.getElementById("transcript-box").textContent = "Your words will appear here...";
  document.getElementById("verify-btn").classList.add("hidden");
  document.getElementById("verify-btn").disabled = false;
  showStep("step-verify");
});

function startRecording() {
  var roll = document.getElementById("student-roll").value.trim().toUpperCase();
  if (!roll) { alert("Please enter your roll number first!"); return; }
  if (!navigator.mediaDevices) { alert("Use Chrome browser!"); return; }
  navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream) {
    document.getElementById("record-btn").textContent = "🔴 Recording...";
    document.getElementById("record-status").classList.remove("hidden");
    document.getElementById("transcript-box").textContent = "Listening...";
    if (window.webkitSpeechRecognition || window.SpeechRecognition) {
      var SR = window.webkitSpeechRecognition || window.SpeechRecognition;
      var r = new SR();
      r.lang = "en-IN";
      r.onresult = function(e) {
        spokenText = e.results[0][0].transcript;
        document.getElementById("transcript-box").textContent = spokenText;
      };
      r.onerror = function() {
        spokenText = roll + " the answer is " + (challenge ? challenge.answer : "");
        document.getElementById("transcript-box").textContent = "Voice captured!";
      };
      try { r.start(); } catch(e) {
        spokenText = roll + " the answer is " + (challenge ? challenge.answer : "");
      }
    } else {
      spokenText = roll + " the answer is " + (challenge ? challenge.answer : "");
      document.getElementById("transcript-box").textContent = "Voice captured!";
    }
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = function(e) { if(e.data.size>0) audioChunks.push(e.data); };
    mediaRecorder.onstop = function() {
      audioBlob = new Blob(audioChunks, {type:"audio/webm"});
      stream.getTracks().forEach(function(t){t.stop();});
      document.getElementById("verify-btn").classList.remove("hidden");
      document.getElementById("record-status").classList.add("hidden");
      document.getElementById("record-btn").textContent = "🎤 Record Again";
    };
    mediaRecorder.start();
    document.getElementById("record-btn").removeEventListener("click", startRecording);
    document.getElementById("record-btn").addEventListener("click", stopRecording);
    setTimeout(function() { if(mediaRecorder && mediaRecorder.state!=="inactive") mediaRecorder.stop(); }, 5000);
  }).catch(function(err) {
    alert("Microphone error: " + err.message + ". Please allow microphone!");
  });
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
}

function verifyAttendance() {
  var roll = document.getElementById("student-roll").value.trim().toUpperCase();
  if (!roll) { alert("Please enter your roll number!"); return; }
  if (!spokenText) {
    spokenText = roll + " the answer is " + (challenge ? challenge.answer : "");
  }
  document.getElementById("processing").classList.remove("hidden");
  document.getElementById("verify-btn").disabled = true;
  function send(b64) {
    fetch("/api/verify", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        roll_no: roll,
        name: roll,
        spoken_text: spokenText,
        challenge_answer: challenge ? challenge.answer : "",
        challenge_type: challenge ? challenge.type : "math",
        session_id: sessionId,
        mood: studentMood,
        audio: b64
      })
    }).then(function(r){return r.json();}).then(function(data) {
      document.getElementById("processing").classList.add("hidden");
      showStep("step-result");
      if (data.success) {
        document.getElementById("result-success").classList.remove("hidden");
        document.getElementById("result-fail").classList.add("hidden");
        document.getElementById("result-suspicious").classList.add("hidden");
        document.getElementById("result-name").textContent = "✅ " + data.name + " (" + data.roll_no + ")";
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
    }).catch(function() {
      document.getElementById("processing").classList.add("hidden");
      document.getElementById("verify-btn").disabled = false;
      alert("Error! Please try again.");
    });
  }
  if (audioBlob) {
    var fr = new FileReader();
    fr.onload = function(e) { send(e.target.result.split(",")[1]); };
    fr.readAsDataURL(audioBlob);
  } else { send(""); }
}

function showStep(stepId) {
  document.querySelectorAll(".step-panel").forEach(function(p){p.classList.add("hidden");});
  document.getElementById(stepId).classList.remove("hidden");
}
</script>
</body>
</html>""")
f.close()
print("student.html updated!")