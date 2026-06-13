"""
Run this file directly to test each component of the voice pipeline in isolation.
Usage: python test_voice.py
"""

import os
from dotenv import load_dotenv

load_dotenv()


def test_dotenv():
    print("\n--- Step 1: .env loading ---")
    api_key = os.environ.get("GROQ_API_KEY", "")
    if api_key:
        print(f"[OK] GROQ_API_KEY loaded (starts with: {api_key[:8]}...)")
    else:
        print("[FAIL] GROQ_API_KEY not found — check your .env file")
    return api_key


def test_tts():
    print("\n--- Step 2: gTTS test ---")
    try:
        from gtts import gTTS
        from io import BytesIO

        buf = BytesIO()
        gTTS("Hello, this is a voice test from your AI gym coach.").write_to_fp(buf)
        buf.seek(0)
        data = buf.read()

        if len(data) > 0:
            print(f"[OK] gTTS working — generated {len(data)} bytes of audio")

            with open("test_audio.mp3", "wb") as f:
                f.write(data)
            print("[OK] Saved to test_audio.mp3 — play it to verify sound")
        else:
            print("[FAIL] gTTS returned empty audio")
    except Exception as e:
        print(f"[FAIL] gTTS failed: {e}")


def test_llm(api_key):
    print("\n--- Step 3: Groq LLM test ---")
    if not api_key:
        print("[SKIP] Skipping — no API key found")
        return

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say exactly: Voice pipeline is working!"}],
            temperature=0,
        )
        text = res.choices[0].message.content.strip()
        print(f"[OK] LLM response: {text}")
    except Exception as e:
        print(f"[FAIL] LLM failed: {e}")


def test_full_pipeline(api_key):
    print("\n--- Step 4: Full pipeline test ---")
    if not api_key:
        print("[SKIP] Skipping — no API key found")
        return

    try:
        from services.coaching.llm import LLMCoach
        from services.coaching.tts import TextToSpeech
        from services.coaching.voice_pipeline import VoicePipeline
        from groq import Groq

        client = Groq(api_key=api_key)
        pipeline = VoicePipeline(LLMCoach(client), TextToSpeech())

        result = pipeline.process_event(
            event="login",
            exercise="",
            metrics={"issue": "The user's name is Tester. Greet them."}
        )

        if result:
            audio, text = result
            print(f"[OK] Pipeline working — Coach said: \"{text}\"")
            print(f"[OK] Audio bytes: {len(audio)}")

            with open("test_pipeline_audio.mp3", "wb") as f:
                f.write(audio)
            print("[OK] Saved to test_pipeline_audio.mp3")
        else:
            print("[FAIL] Pipeline returned None")
    except Exception as e:
        print(f"[FAIL] Full pipeline failed: {e}")


if __name__ == "__main__":
    api_key = test_dotenv()
    test_tts()
    test_llm(api_key)
    test_full_pipeline(api_key)
    print("\n--- Done ---")
