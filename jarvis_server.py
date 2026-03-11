import sounddevice as sd
from scipy.io.wavfile import write
import whisper
from pynput import keyboard
import requests
import numpy as np
import os
import asyncio
import edge_tts
import subprocess
import websockets
import json
import threading

# ========== CONFIGURATION ==========
SAMPLERATE = 16000
MODEL_NAME = "base"
OLLAMA_MODEL = "mistral:7b"
REQUEST_TIMEOUT = 60
EDGE_VOICE = "en-GB-RyanNeural"
WS_PORT = 8765

# ========== GLOBAL STATE ==========
recording = []
is_recording = False
whisper_model = None
conversation_history = []
connected_clients = set()
event_loop = None

# ========== WEBSOCKET BROADCAST ==========
async def broadcast(event: str, data: dict = {}):
    """Send a JSON event to all connected frontend clients."""
    if not connected_clients:
        return
    message = json.dumps({"event": event, **data})
    await asyncio.gather(
        *[ws.send(message) for ws in connected_clients],
        return_exceptions=True
    )

def emit(event: str, data: dict = {}):
    """Thread-safe fire-and-forget broadcast from sync code."""
    if event_loop and event_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast(event, data), event_loop)

async def ws_handler(websocket):
    connected_clients.add(websocket)
    print(f"🌐 Frontend connected ({len(connected_clients)} clients)")
    try:
        await broadcast("status", {"state": "standby"})
        async for _ in websocket:
            pass  # We only push; frontend doesn't send messages
    finally:
        connected_clients.discard(websocket)
        print("🌐 Frontend disconnected")

# ========== INITIALIZATION ==========
def initialize():
    global whisper_model
    print("🔄 Loading Whisper model...")
    whisper_model = whisper.load_model(MODEL_NAME)
    print("✅ Model loaded\n")

# ========== AUDIO ==========
def audio_callback(indata, frames, time, status):
    if is_recording:
        recording.append(indata.copy())

def start_recording():
    global recording, is_recording
    recording = []
    is_recording = True
    emit("status", {"state": "listening"})
    print("🎤 Recording...")

def stop_recording():
    global is_recording
    is_recording = False

    if len(recording) == 0:
        print("⚠️  No audio")
        emit("status", {"state": "standby"})
        return False

    audio = np.concatenate(recording, axis=0)
    write("input.wav", SAMPLERATE, audio)
    print("⏹️  Stopped")
    return True

# ========== TRANSCRIPTION ==========
def transcribe():
    if not os.path.exists("input.wav"):
        return None

    print("🔄 Transcribing...")
    emit("status", {"state": "thinking"})
    result = whisper_model.transcribe("input.wav", fp16=False)
    text = result["text"].strip()

    # Confidence check via no_speech_prob
    segments = result.get("segments", [])
    if segments:
        avg_no_speech_prob = sum(s["no_speech_prob"] for s in segments) / len(segments)
        if avg_no_speech_prob > 0.4:
            print(f"⚠️  Low confidence ({avg_no_speech_prob:.2f}), discarding")
            return "__unclear__"

    if len(text) < 2:
        return None

    return text

# ========== AI RESPONSE ==========
def get_response(user_text):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "system": """You are Jarvis, a highly intelligent British AI assistant modelled after the AI from Iron Man.
Your rules:
- Always respond in one to three sentences; never fewer than one or more than three.
- Be precise, dry, and occasionally witty — like a butler wnpho also has a PhD.
- If you genuinely don't know something, say: "I'm afraid that falls outside my current knowledge, sir."
- If the question seems garbled or nonsensical, say: "I'm not quite sure I follow, sir. Could you rephrase that?"
- Never invent facts, people, organisations, or events.
- Never ask follow-up questions.
- Never break character.""",
                "prompt": user_text,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "top_p": 0.9,
                    "num_predict": 80,
                    "stop": ["User:", "Human:", "\n", "Jarvis:"]
                }
            },
            timeout=REQUEST_TIMEOUT
        )

        result = response.json()["response"].strip()

        # Remove any accidental role labels Mistral sometimes adds
        for label in ["Jarvis:", "Assistant:", "AI:", "JARVIS:"]:
            if result.startswith(label):
                result = result[len(label):].strip()

        # Hard cut to first sentence
        for punct in [".", "!", "?"]:
            idx = result.find(punct)
            if idx != -1 and idx > 10:  # avoid cutting too early on e.g. "Mr."
                result = result[:idx + 1]
                break

        return result if result else "I'm afraid I have nothing to add on that, sir."

    except requests.exceptions.ConnectionError:
        return "Error: Ollama not running."
    except requests.exceptions.Timeout:
        return "Error: Response timed out."
    except Exception as e:
        return f"Error: {e}"
# ========== TEXT-TO-SPEECH ==========
async def speak_async(text):
    try:
        tts = edge_tts.Communicate(text=text, voice=EDGE_VOICE)
        await tts.save("speech.mp3")
    except Exception as e:
        print(f"⚠️  TTS error: {e}")

def speak(text):
    emit("status", {"state": "speaking"})
    asyncio.run(speak_async(text))
    if os.path.exists("speech.mp3"):
        subprocess.run(["afplay", "speech.mp3"], check=False)
    emit("status", {"state": "standby"})

# ========== PROCESS SPEECH ==========
def process_speech():
    user_text = transcribe()

    if user_text == "__unclear__" or not user_text:
        msg = "Sorry sir, I didn't quite catch that. Could you say it again?"
        print(f"⚠️  Unclear audio")
        emit("transcript", {"speaker": "jarvis", "text": msg})
        speak(msg)
        return True

    print(f"💬 You: {user_text}")
    emit("transcript", {"speaker": "user", "text": user_text})

    quit_words = ["quit", "exit", "goodbye", "bye", "stop", "shut down"]
    if any(word in user_text.lower() for word in quit_words):
        emit("transcript", {"speaker": "jarvis", "text": "Goodbye sir."})
        speak("Goodbye sir.")
        print("👋 Goodbye!")
        return False

    print("🤔 Thinking...")
    ai_response = get_response(user_text)
    print(f"🤖 Jarvis: {ai_response}\n")
    emit("transcript", {"speaker": "jarvis", "text": ai_response})

    if not ai_response.startswith("Error:"):
        speak(ai_response)
    else:
        emit("status", {"state": "standby"})

    return True

# ========== KEYBOARD HANDLERS ==========
def on_press(key):
    global is_recording
    if key == keyboard.Key.space and not is_recording:
        start_recording()

def on_release(key):
    global is_recording

    if key == keyboard.Key.space and is_recording:
        if stop_recording():
            should_continue = process_speech()
            if not should_continue:
                return False

    if key == keyboard.Key.esc:
        print("\n👋 Shutting down...")
        return False

# ========== WEBSOCKET SERVER THREAD ==========
def run_ws_server():
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)

    async def serve():
        async with websockets.serve(ws_handler, "localhost", WS_PORT):
            print(f"🌐 WebSocket server running on ws://localhost:{WS_PORT}")
            await asyncio.Future()  # Run forever

    event_loop.run_until_complete(serve())

# ========== MAIN ==========
def main():
    print("=" * 50)
    print("🧠 JARVIS AI ASSISTANT")
    print("=" * 50)

    initialize()

    # Start WebSocket server in background thread
    ws_thread = threading.Thread(target=run_ws_server, daemon=True)
    ws_thread.start()

    print("Hold SPACE to record")
    print("Release SPACE to process")
    print("Press ESC to quit\n")

    try:
        with sd.InputStream(callback=audio_callback, channels=1, samplerate=SAMPLERATE):
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
    except KeyboardInterrupt:
        print("\n👋 Interrupted")
    finally:
        for f in ["input.wav", "speech.mp3"]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    main()
