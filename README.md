# 🤖 Mini Jarvis

A fully offline, voice-activated AI assistant with a British personality. You talk, it listens, it responds. No cloud, no API keys, no internet required.

It started as a Whisper experiment. It got out of hand.

---

## What it does

- 🎤 Hold `SPACE` to talk, release to process
- 🧠 Whisper transcribes your voice locally
- 💬 Mistral 7B (via Ollama) generates a response
- 🔊 Edge TTS reads it back in a British accent
- 🖥️ Arc Reactor desktop UI built in Svelte + Tauri

Everything runs on your machine. No subscriptions. No data leaving your laptop.

---

## Why it exists

I wanted to learn Whisper. That was it. That was the whole plan.

Then I got curious about TTS voices. Then local LLMs. Then I thought it'd be funny to make it sound like Jarvis from Iron Man. Then I figured if I'd already spent this long on it, I may as well give it a proper UI.

It's not trying to be anything groundbreaking. It's a personal project I built to use in places without reliable Wi-Fi — libraries, cafés, airports — when I just want to ask something quickly and get a sensible answer back.

---

## The TTS saga (abbreviated)

Three TTS libraries. Days of environment conflicts. Zero working voices I actually liked.

- **Piper** — never got it running
- **Coqui TTS** — ran fine, sounded rough
- **XTTS v2** — version hell, never resolved

Eventually switched to **Edge TTS**. Took ten minutes. Sounded great. Lesson learned.

---

## Requirements

**System dependencies**
- [Ollama](https://ollama.com) — runs Mistral locally
- [Node.js](https://nodejs.org) — for the frontend
- [Rust](https://rustup.rs) — required by Tauri

**Python**
```bash
pip install -r requirements.txt
```

---

## Setup

```bash
# 1. Pull the model
ollama pull mistral:7b

# 2. Install Python deps
pip install -r requirements.txt

# 3. Install frontend deps
cd jarvis-ui && npm install
```

---

## Running

Two terminals. Both need to be open.

```bash
# Terminal 1
python jarvis_server.py

# Terminal 2
cd jarvis-ui && npm run tauri dev
```

Hold `SPACE` to speak. Release to process. `ESC` to quit.

> First run of `npm run tauri dev` takes 5–10 minutes while Rust compiles. Every run after that is fast.

---

## How it works

```
SPACE held       →  mic records via sounddevice
SPACE released   →  Whisper transcribes (low-confidence audio gets discarded)
                 →  Mistral generates a short response via Ollama
                 →  Edge TTS speaks it back
                 →  WebSocket pushes state + transcript to the UI in real time
```

---

## Limitations

- No internet awareness — Mistral's knowledge cuts off early 2024
- Responses are capped short by design — not ideal for deep questions
- No memory between sessions — it forgets everything the moment you close it
- macOS only for now — uses `afplay` for audio; swap it for `mpg123` on Linux

---

## License

MIT. Take it, break it, improve it.
