"""
sample.py — ANSH Local Voice Recording & Full Test Suite
Records user voice sample from microphone, saves to data/voice_samples/my_voice.wav,
and tests ANSH Local Custom Voice Engine playback.
"""
import os
import sys
import time
import wave
import numpy as np
import sounddevice as sd

from core.tts import create_tts_player

VOICE_DIR = os.path.join("data", "voice_samples")
OUTPUT_WAV = os.path.join(VOICE_DIR, "my_voice.wav")
SAMPLE_RATE = 24000
RECORD_SECONDS = 5


def save_wav(filename: str, audio_data: np.ndarray, sample_rate: int = 24000):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    audio_int16 = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())


def main():
    print("=" * 60)
    print("      ANSH AI — Local Voice Recording & Setup Test")
    print("=" * 60)
    print("\n[Step 1] Preparing microphone recording...")
    print("Please get ready to speak a short sample sentence (e.g., 'Hello, I am Anshu, ANSH AI active!').")

    for i in range(3, 0, -1):
        print(f"  Starting in {i}...")
        time.sleep(1.0)

    print("\n[Step 2] RECORDING NOW! (Speak clearly for 5 seconds)...")
    recording = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')

    for i in range(RECORD_SECONDS, 0, -1):
        print(f"  Recording... {i}s remaining")
        time.sleep(1.0)

    sd.wait()
    print("\n[Step 3] Recording complete! Processing audio...")

    save_wav(OUTPUT_WAV, recording, SAMPLE_RATE)
    print(f"  Saved local voice sample to: {OUTPUT_WAV}")

    print("\n[Step 4] Testing ANSH Local Custom Voice Engine playback...")
    player = create_tts_player({"tts_engine": "local"})
    print("  Playing back recorded voice using LocalCustomVoiceEngine...")
    player.speak("Testing local voice")

    print("\n" + "=" * 60)
    print("  Local Voice Enrollment & Full Test Complete!")
    print("  Your voice is now set as the active local voice in ANSH AI!")
    print("=" * 60)


if __name__ == "__main__":
    main()
