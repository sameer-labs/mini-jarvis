import subprocess
import os

print("🎙️  Testing Jarvis voice...")

# Generate
print("⏳ Generating speech...")
subprocess.run([
    "tts",
    "--text", "Good evening sir. All systems are operational.",
    "--model_name", "tts_models/en/vctk/vits",
    "--speaker_idx", "p318",
    "--out_path", "jarvis_test.wav"
])

# Check file
if os.path.exists("jarvis_test.wav"):
    print("✅ Generated jarvis_test.wav")
    print("▶️  Playing...")
    subprocess.run(["afplay", "jarvis_test.wav"])
else:
    print("❌ File not created")