# Placeholder for LiveKit-integrated real-time voice assistant backend
# (Python-based starter with Whisper + GPT + pyttsx3 + WebRTC signaling skeleton)

# NOTE: This assumes you're using LiveKit client SDK in the frontend (e.g., React)
# and a LiveKit server/cloud instance is available.

import asyncio
import json
import os
from faster_whisper import WhisperModel
from openai import OpenAI
import pyttsx3
import websockets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
FORCE_CPU = os.getenv("FORCE_CPU") == "1"

# Initialize GPT and Whisper
device = "cpu" if FORCE_CPU else "cuda"
whisper_model = WhisperModel("base", compute_type="int8", device=device)
client = OpenAI(api_key=OPENAI_KEY)
tts = pyttsx3.init()

# Simulated voice assistant pipeline using WebSocket
connected_clients = set()

async def process_audio_and_respond(websocket, audio_bytes):
    try:
        import numpy as np
        import soundfile as sf
        from io import BytesIO

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        wav_io = BytesIO()
        sf.write(wav_io, audio_np, 16000, format='WAV', subtype='PCM_16')
        wav_io.seek(0)

        segments, _ = whisper_model.transcribe(wav_io, beam_size=1, language="en")
        segments = list(segments)
        if not segments:
            await websocket.send(json.dumps({"type": "error", "data": "No speech detected."}))
            return

        full_text = " ".join([seg.text.strip() for seg in segments])
        await websocket.send(json.dumps({"type": "transcript", "data": full_text}))

        messages = [
            {"role": "system", "content": "You are a helpful AI interviewer."},
            {"role": "user", "content": full_text}
        ]
        assistant_response = ""
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            stream=True
        )
        for part in stream:
            if part.choices:
                delta = part.choices[0].delta.get("content", "")
                if delta:
                    assistant_response += delta
                    await websocket.send(json.dumps({"type": "gpt", "data": delta}))

        # Speak using pyttsx3 (local only)
        tts.say(assistant_response)
        tts.runAndWait()

    except Exception as e:
        await websocket.send(json.dumps({"type": "error", "data": f"Processing error: {str(e)}"}))


async def handler(websocket):
    connected_clients.add(websocket)
    print("Client connected")
    buffer = b""
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                buffer += message
            elif isinstance(message, str):
                data = json.loads(message)
                if data.get("type") == "flush":
                    await process_audio_and_respond(websocket, buffer)
                    buffer = b""
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        connected_clients.remove(websocket)


async def main():
    async with websockets.serve(handler, "localhost", 8765, max_size=None):
        print("WebSocket server running at ws://localhost:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
