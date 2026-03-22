register = open('templates/register.html', 'w', encoding='utf-8')
register.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Register Student</title>
<link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
<div class="container">
  <header>
    <a href="/" class="back-btn">Home</a>
    <h1>Register Students</h1>
  </header>

  <div class="panel">
    <h2>Add New Student</h2>
    <div class="name-row" style="margin-bottom:1rem">
      <input type="text" id="new-name" placeholder="Enter student full name"/>
    </div>
    <div class="record-section">
      <button class="btn btn-mic btn-large" id="record-btn" onclick="startRecording()">Start Voice Recording</button>
      <div class="record-status hidden" id="record-status">
        <div class="pulse-ring"></div>
        <span>Recording... speak now</span>
      </div>
      <div class="transcript-box" id="transcript-box">Your spoken words will appear here...</div>
    </div>
    <button class="btn btn-primary btn-large hidden" id="save-btn" onclick="saveStudent()">Save Student</button>
    <div class="response-box" id="save-response"></div>
  </div>

  <div class="panel">
    <h2>Registered Students</h2>
    <button class="btn btn-secondary" onclick="loadStudents()">Refresh List</button>
    <div id="students-list" style="margin-top:1rem"></div>
  </div>
</div>
<script src="/static/js/murf.js"></script>
<script>
let mediaRecorder = null;
let audioChunks = [];
let audioBlob = null;
let spokenText = "";

async function startRecording() {
  const name = document.getElementById("new-name").value.trim();
  if (!name) { alert("Please enter student name first!"); return; }

  if (!navigator.mediaDevices) { alert("Microphone not supported!"); return; }

  const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang = "en-IN";
  recognition.onresult = (e) => {
    spokenText = e.results[0][0].transcript;
    document.getElementById("transcript-box").textContent = spokenText;
  };
  recognition.start();

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];
  mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
  mediaRecorder.onstop = () => {
    audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    document.getElementById("save-btn").classList.remove("hidden");
    document.getElementById("record-status").classList.add("hidden");
    document.getElementById("record-btn").textContent = "Record Again";
  };
  mediaRecorder.start();
  document.getElementById("record-btn").textContent = "Stop Recording";
  document.getElementById("record-btn").onclick = stopRecording;
  document.getElementById("record-status").classList.remove("hidden");
  setTimeout(stopRecording, 5000);
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    document.getElementById("record-btn").textContent = "Record Again";
    document.getElementById("record-btn").onclick = startRecording;
  }
}

async function saveStudent() {
  const name = document.getElementById("new-name").value.trim();
  if (!name) { alert("Please enter a name!"); return; }

  let audioB64 = "";
  if (audioBlob) {
    const buf = await audioBlob.arrayBuffer();
    audioB64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
  }

  const res = await fetch("/api/register-student", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name, audio: audioB64, spoken_text: spokenText })
  });
  const data = await res.json();

  if (data.success) {
    document.getElementById("save-response").textContent = name + " registered successfully!";
    document.getElementById("save-response").style.color = "#4ade80";
    document.getElementById("new-name").value = "";
    document.getElementById("transcript-box").textContent = "Your spoken words will appear here...";
    document.getElementById("save-btn").classList.add("hidden");
    await speak(name + " has been registered successfully!");
    loadStudents();
  } else {
    document.getElementById("save-response").textContent = "Error: " + data.reason;
    document.getElementById("save-response").style.color = "#ef4444";
  }
}

async function loadStudents() {
  const res = await fetch("/api/student-list");
  const data = await res.json();
  const list = document.getElementById("students-list");
  if (data.students.length === 0) {
    list.innerHTML = "<p style='color:var(--text-muted)'>No students registered yet</p>";
    return;
  }
  list.innerHTML = data.students.map((s, i) =>
    "<div class='leader-row'>" +
    "<span class='medal'>" + (i+1) + "</span>" +
    "<span class='leader-name'>" + s.name + "</span>" +
    "<span class='leader-days' style='color:" + (s.has_voice ? "#4ade80" : "#f59e0b") + "'>" +
    (s.has_voice ? "Voice Registered" : "No Voice") + "</span>" +
    "<button class='btn btn-small' style='background:#ef4444;color:white;margin-left:8px' onclick='deleteStudent(\"" + s.name + "\")'>Remove</button>" +
    "</div>"
  ).join("");
}

async function deleteStudent(name) {
  if (!confirm("Remove " + name + "?")) return;
  const res = await fetch("/api/delete-student", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  });
  const data = await res.json();
  if (data.success) { await speak(name + " removed."); loadStudents(); }
}

loadStudents();
</script>
</body>
</html>""")
register.close()
print("register.html created!")