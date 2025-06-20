import asyncio
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from faster_whisper import WhisperModel
import openai
import azure.cognitiveservices.speech as speechsdk

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")

app = FastAPI()
whisper_model = WhisperModel("base", compute_type="int8")

import logging

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# --- Azure Streaming TTS Generator ---
async def tts_stream(text: str):
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    # Use pull stream for async audio generation
    stream = speechsdk.audio.PullAudioOutputStream.create_pull_stream()
    audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config, audio_config)

    # Trigger synthesis
    done = asyncio.Event()

    def on_completed(evt):
        done.set()

    synthesizer.synthesis_completed.connect(on_completed)
    synthesizer.speak_text_async(text)

    while not done.is_set():
        chunk = stream.read(4096)
        if chunk:
            yield chunk
        await asyncio.sleep(0.01)

# --- WebSocket Audio Stream ---
@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connected")
    buffer = b""

    try:
        while True:
            chunk = await websocket.receive_bytes()
            buffer += chunk

            # Process when buffer exceeds 1 second of 16kHz PCM
            if len(buffer) >= 32000:
                segments, _ = whisper_model.transcribe(buffer, beam_size=1, language="en")
                for segment in segments:
                    text = segment.text.strip()
                    if not text:
                        continue

                    # Send transcript
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "data": text
                    }))

                    # GPT-4 streaming
                    gpt_response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": text}],
                        stream=True
                    )
                    assistant_response = ""
                    for part in gpt_response:
                        delta = part["choices"][0]["delta"].get("content", "")
                        if delta:
                            assistant_response += delta
                            await websocket.send_text(json.dumps({
                                "type": "gpt",
                                "data": delta
                            }))

                    # TTS Streaming for assistant reply
                    async for audio_chunk in tts_stream(assistant_response):
                        await websocket.send_bytes(audio_chunk)

                buffer = b""  # reset after processing

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
