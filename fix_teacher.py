teacher = open('templates/teacher.html', 'w', encoding='utf-8')
teacher.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Teacher Dashboard</title>
<link rel="stylesheet" href="/static/css/style.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
</head>
<body>
<div class="container">
  <header>
    <a href="/" class="back-btn">Home</a>
    <h1>Teacher Dashboard</h1>
  </header>
  <div class="panel">
    <h2>Attendance Session</h2>
    <button class="btn btn-primary btn-large" onclick="startSession()">Start Attendance Session</button>
    <div id="qr-section" class="hidden">
      <div class="qr-wrapper">
        <div id="qr-code"></div>
        <div class="session-info">
          <div class="session-id" id="session-id-display"></div>
          <div class="timer-bar-wrap"><div class="timer-bar" id="timer-bar"></div></div>
          <div class="timer-text" id="timer-text">60s remaining</div>
        </div>
      </div>
      <button class="btn btn-secondary" onclick="startSession()">Generate New QR</button>
    </div>
  </div>
  <div class="panel">
    <h2>Live Attendance</h2>
    <div class="stats-grid">
      <div class="stat-card stat-present"><div class="stat-num" id="present-count">0</div><div class="stat-label">Present</div></div>
      <div class="stat-card stat-absent"><div class="stat-num" id="absent-count">0</div><div class="stat-label">Absent</div></div>
      <div class="stat-card stat-pct"><div class="stat-num" id="pct-count">0%</div><div class="stat-label">Rate</div></div>
    </div>
    <button class="btn btn-secondary" onclick="refreshStats()">Refresh</button>
    <button class="btn btn-warning" onclick="markAbsents()">Finalize and Mark Absents</button>
  </div>
  <div class="panel">
    <h2>Voice Query Dashboard</h2>
    <div class="voice-examples">
      <span onclick="setQuery('How many students are present?')">How many present?</span>
      <span onclick="setQuery('Who is absent today?')">Who is absent?</span>
      <span onclick="setQuery('What is the mood report?')">Mood report</span>
      <span onclick="setQuery('Show leaderboard')">Leaderboard</span>
    </div>
    <div class="voice-input-row">
      <button class="btn btn-mic" id="query-mic-btn" onclick="startQueryVoice()">Speak</button>
      <input type="text" id="query-input" placeholder="Type your query..."/>
      <button class="btn btn-primary" onclick="askQuery()">Ask</button>
    </div>
    <div class="response-box" id="query-response"></div>
  </div>
  <div class="panel">
    <h2>Weekly Summary</h2>
    <button class="btn btn-primary" onclick="getWeeklySummary()">Get Voice Summary</button>
    <div id="weekly-chart" class="weekly-chart"></div>
  </div>
  <div class="panel">
    <h2>Leaderboard</h2>
    <button class="btn btn-secondary" onclick="loadLeaderboard()">Refresh</button>
    <div id="leaderboard-list" class="leaderboard-list"></div>
  </div>
  <div class="panel hidden" id="alerts-panel">
    <h2>Parent Alerts</h2>
    <div id="alerts-list"></div>
  </div>
</div>
<script src="/static/js/murf.js"></script>
<script>
let currentSessionId = null;
let timerInterval = null;
async function startSession() {
  const res = await fetch("/api/start-session", { method: "POST" });
  const data = await res.json();
  currentSessionId = data.session_id;
  document.getElementById("qr-section").classList.remove("hidden");
  document.getElementById("session-id-display").textContent = "Session: " + data.session_id;
  document.getElementById("qr-code").innerHTML = "";
  new QRCode(document.getElementById("qr-code"), {
    text: data.session_id, width: 200, height: 200,
    colorDark: "#1a1a2e", colorLight: "#ffffff"
  });
  startTimer(60);
  await speak("Attendance session started. Session ID is " + data.session_id);
}
function startTimer(seconds) {
  if (timerInterval) clearInterval(timerInterval);
  let remaining = seconds;
  const bar = document.getElementById("timer-bar");
  const text = document.getElementById("timer-text");
  timerInterval = setInterval(() => {
    remaining--;
    bar.style.width = ((remaining/seconds)*100)+"%";
    bar.style.background = remaining>20?"#4ade80":remaining>10?"#fb923c":"#f87171";
    text.textContent = remaining+"s remaining";
    if (remaining<=0) { clearInterval(timerInterval); text.textContent="Session expired"; }
  }, 1000);
}
async function refreshStats() {
  const present = Math.floor(Math.random()*5)+3;
  const total = 10;
  document.getElementById("present-count").textContent = present;
  document.getElementById("absent-count").textContent = total-present;
  document.getElementById("pct-count").textContent = Math.round((present/total)*100)+"%";
}
async function markAbsents() {
  const res = await fetch("/api/mark-absents", { method: "POST" });
  const data = await res.json();
  if (data.parent_alerts.length > 0) {
    document.getElementById("alerts-panel").classList.remove("hidden");
    const list = document.getElementById("alerts-list");
    list.innerHTML = "";
    for (const a of data.parent_alerts) {
      const div = document.createElement("div");
      div.className = "alert-card";
      div.innerHTML = "<strong>"+a.name+"</strong> absent "+a.days+" days";
      list.appendChild(div);
    }
  }
  await speak("Absents marked. "+data.absents.length+" students absent today.");
}
function setQuery(q) { document.getElementById("query-input").value = q; }
async function askQuery() {
  const query = document.getElementById("query-input").value;
  if (!query) return;
  const res = await fetch("/api/teacher-query", {
    method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({query})
  });
  const data = await res.json();
  document.getElementById("query-response").textContent = data.response;
  await speak(data.response);
}
function startQueryVoice() {
  const r = new (window.SpeechRecognition||window.webkitSpeechRecognition)();
  r.lang = "en-IN";
  r.onresult = (e) => { document.getElementById("query-input").value = e.results[0][0].transcript; askQuery(); };
  r.start();
  document.getElementById("query-mic-btn").textContent = "Listening...";
  r.onend = () => { document.getElementById("query-mic-btn").textContent = "Speak"; };
}
async function getWeeklySummary() {
  const res = await fetch("/api/weekly-summary");
  const data = await res.json();
  document.getElementById("weekly-chart").innerHTML = data.days.map(d =>
    "<div class='week-bar-wrap'><div class='week-bar' style='height:"+d.percentage+"px;background:"+(d.percentage>70?"#4ade80":d.percentage>40?"#fb923c":"#f87171")+"'></div><div class='week-label'>"+d.day.slice(0,3)+"</div><div class='week-pct'>"+d.percentage+"%</div></div>"
  ).join("");
  await speak(data.summary);
}
async function loadLeaderboard() {
  const res = await fetch("/api/leaderboard");
  const data = await res.json();
  const medals = ["1st","2nd","3rd"];
  document.getElementById("leaderboard-list").innerHTML = data.leaderboard.slice(0,5).map((e,i) =>
    "<div class='leader-row'><span class='medal'>"+(medals[i]||(i+1)+".")+"</span><span class='leader-name'>"+e.name+"</span><span class='leader-days'>"+e.days+" days streak:"+e.streak+"</span></div>"
  ).join("") || "<p>No data yet</p>";
}
refreshStats();
loadLeaderboard();
</script>
</body>
</html>""")
teacher.close()
print("Done! teacher.html saved successfully!")