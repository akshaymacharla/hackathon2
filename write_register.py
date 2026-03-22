html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Register</title>
<link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
<div class="container">
<header>
<a href="/" class="back-btn">Home</a>
<h1>Register Your Voice</h1>
</header>
<div class="panel">
<h2>Enter Your Name</h2>
<input type="text" id="myname" placeholder="Type your full name"/>
</div>
<div class="panel">
<h2>Record Your Voice</h2>
<p class="hint">Say: My name is [Your Name] and I am registering</p>
<button class="btn btn-mic btn-large" id="recbtn">🎤 Start Recording</button>
<div id="recstatus" style="display:none;color:#ef4444;margin:1rem 0">🔴 Recording... speak now</div>
<div class="transcript-box" id="words">Your words appear here...</div>
</div>
<div class="panel" id="savepanel" style="display:none">
<h2>Save Registration</h2>
<button class="btn btn-primary btn-large" id="savebtn">✅ Save My Voice</button>
<div id="savemsg" style="margin-top:1rem;font-size:1rem"></div>
</div>
<div class="panel">
<h2>Registered Students</h2>
<button class="btn btn-secondary" id="refreshbtn">Refresh List</button>
<div id="studlist" style="margin-top:1rem"></div>
</div>
</div>
<script>
var myBlob = null;
var myRec = null;
var myChunks = [];
var myWords = "";

document.getElementById("recbtn").addEventListener("click", function() {
  var name = document.getElementById("myname").value.trim();
  if (!name) { alert("Enter your name first!"); return; }
  if (!navigator.mediaDevices) { alert("Use Chrome browser!"); return; }
  navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream) {
    document.getElementById("recbtn").textContent = "🔴 Recording...";
    document.getElementById("recstatus").style.display = "block";
    document.getElementById("words").textContent = "Listening...";
    if (window.webkitSpeechRecognition || window.SpeechRecognition) {
      var SR = window.webkitSpeechRecognition || window.SpeechRecognition;
      var r = new SR();
      r.lang = "en-IN";
      r.onresult = function(e) {
        myWords = e.results[0][0].transcript;
        document.getElementById("words").textContent = myWords;
      };
      r.onerror = function() {
        myWords = name;
        document.getElementById("words").textContent = "Voice captured!";
      };
      try { r.start(); } catch(e) { myWords = name; }
    } else {
      myWords = name;
      document.getElementById("words").textContent = "Voice captured!";
    }
    myRec = new MediaRecorder(stream);
    myChunks = [];
    myRec.ondataavailable = function(e) { if(e.data.size>0) myChunks.push(e.data); };
    myRec.onstop = function() {
      myBlob = new Blob(myChunks, {type:"audio/webm"});
      stream.getTracks().forEach(function(t){t.stop();});
      document.getElementById("savepanel").style.display = "block";
      document.getElementById("recstatus").style.display = "none";
      document.getElementById("recbtn").textContent = "🎤 Record Again";
    };
    myRec.start();
    setTimeout(function() {
      if (myRec && myRec.state !== "inactive") myRec.stop();
    }, 5000);
  }).catch(function(err) {
    alert("Microphone error: " + err.message);
  });
});

document.getElementById("savebtn").addEventListener("click", function() {
  var name = document.getElementById("myname").value.trim();
  if (!name) { alert("Enter your name!"); return; }
  var msg = document.getElementById("savemsg");
  msg.textContent = "Saving...";
  msg.style.color = "#94a3b8";
  function send(b64) {
    fetch("/api/register-student", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({name:name, audio:b64, spoken_text:myWords})
    }).then(function(r){return r.json();}).then(function(d) {
      if (d.success) {
        msg.textContent = "✅ " + name + " registered!";
        msg.style.color = "#4ade80";
        document.getElementById("myname").value = "";
        document.getElementById("words").textContent = "Your words appear here...";
        document.getElementById("savepanel").style.display = "none";
        myBlob = null; myWords = "";
        loadList();
      } else {
        msg.textContent = "❌ " + d.reason;
        msg.style.color = "#ef4444";
      }
    }).catch(function() {
      msg.textContent = "❌ Error! Try again.";
      msg.style.color = "#ef4444";
    });
  }
  if (myBlob) {
    var fr = new FileReader();
    fr.onload = function(e) { send(e.target.result.split(",")[1]); };
    fr.readAsDataURL(myBlob);
  } else { send(""); }
});

document.getElementById("refreshbtn").addEventListener("click", loadList);

function loadList() {
  fetch("/api/student-list").then(function(r){return r.json();}).then(function(d) {
    var div = document.getElementById("studlist");
    if (!d.students || d.students.length === 0) {
      div.innerHTML = "<p style='color:#94a3b8'>No students yet</p>";
      return;
    }
    var html = "";
    for (var i=0; i<d.students.length; i++) {
      var s = d.students[i];
      var color = s.has_voice ? "#4ade80" : "#f59e0b";
      var status = s.has_voice ? "✅ Registered" : "⚠️ No Voice";
      html += "<div class='leader-row'>";
      html += "<span class='medal'>" + (i+1) + "</span>";
      html += "<span class='leader-name'>" + s.name + "</span>";
      html += "<span style='font-size:0.82rem;color:" + color + "'>" + status + "</span>";
      html += "<button data-name='" + s.name + "' class='delbtn' style='margin-left:8px;padding:4px 10px;background:#ef4444;color:white;border:none;border-radius:8px;cursor:pointer'>Remove</button>";
      html += "</div>";
    }
    div.innerHTML = html;
    var btns = div.querySelectorAll(".delbtn");
    for (var j=0; j<btns.length; j++) {
      btns[j].addEventListener("click", function() {
        var n = this.getAttribute("data-name");
        if (!confirm("Remove " + n + "?")) return;
        fetch("/api/delete-student", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({name:n})
        }).then(function(){loadList();});
      });
    }
  }).catch(function() {});
}

loadList();
</script>
</body>
</html>"""

with open('templates/register.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Done! Length:", len(html))