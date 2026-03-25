async function speak(text, lang = "en-IN") {
  // Create or get indicator
  let indicator = document.getElementById("tts-indicator");
  if (!indicator) {
    indicator = document.createElement("div");
    indicator.id = "tts-indicator";
    indicator.innerHTML = `
      <div class="tts-pill">
        <span class="tts-icon">🔊</span>
        <span class="tts-text">System Speaking...</span>
      </div>
      <style>
        #tts-indicator {
          position: fixed;
          bottom: 20px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 9999;
          pointer-events: none;
          transition: opacity 0.3s ease;
        }
        .tts-pill {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          padding: 8px 16px;
          border-radius: 20px;
          display: flex;
          align-items: center;
          gap: 8px;
          box-shadow: 0 4px 15px rgba(0,0,0,0.3);
          color: white;
          font-family: inherit;
        }
        .tts-icon { animation: tts-pulse 1s infinite; }
        @keyframes tts-pulse {
          0% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.2); opacity: 0.7; }
          100% { transform: scale(1); opacity: 1; }
        }
      </style>
    `;
    document.body.appendChild(indicator);
  }

  const showIndicator = (show) => {
    indicator.style.opacity = show ? "1" : "0";
  };

  try {
    showIndicator(true);
    const res = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang })
    });
    const data = await res.json();
    if (data.audio_url) {
      const audio = new Audio(data.audio_url);
      return new Promise(resolve => {
        audio.onended = () => { showIndicator(false); resolve(); };
        audio.onerror = () => { showIndicator(false); speakFallback(text, resolve); };
        audio.play().catch(() => { showIndicator(false); speakFallback(text, resolve); });
      });
    } else {
      showIndicator(false);
      return speakFallback(text);
    }
  } catch {
    showIndicator(false);
    return speakFallback(text);
  }
}

function speakFallback(text, resolve) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN";
  utterance.rate = 0.95;
  const voices = speechSynthesis.getVoices();
  const indianVoice = voices.find(v => v.lang.includes("en-IN") || v.name.includes("India"));
  if (indianVoice) utterance.voice = indianVoice;
  utterance.onend = resolve;
  speechSynthesis.speak(utterance);
  if (!resolve) return new Promise(r => { utterance.onend = r; });
}
