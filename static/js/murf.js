async function speak(text, lang = "en-IN") {
  try {
    const res = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang })
    });
    const data = await res.json();
    if (data.audio_url) {
      const audio = new Audio(data.audio_url);
      return new Promise(resolve => {
        audio.onended = resolve;
        audio.onerror = () => speakFallback(text, resolve);
        audio.play().catch(() => speakFallback(text, resolve));
      });
    } else {
      return speakFallback(text);
    }
  } catch {
    return speakFallback(text);
  }
}

function speakFallback(text, resolve) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN";
  utterance.rate = 0.95;
  utterance.pitch = 1.0;
  const voices = speechSynthesis.getVoices();
  const indianVoice = voices.find(v => v.lang.includes("en-IN") || v.name.includes("India"));
  if (indianVoice) utterance.voice = indianVoice;
  utterance.onend = resolve;
  speechSynthesis.speak(utterance);
  if (!resolve) return new Promise(r => { utterance.onend = r; });
}
