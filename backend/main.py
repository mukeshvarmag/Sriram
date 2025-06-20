import asyncio
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from faster_whisper import WhisperModel
import azure.cognitiveservices.speech as speechsdk
from io import BytesIO
from openai import OpenAI
import logging

# Load environment variables
load_dotenv()
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logging.info(f"OpenAI API Key Loaded: {OPENAI_KEY[:12]}...")

# Initialize FastAPI
app = FastAPI()

# Whisper model setup
whisper_model = WhisperModel("base", compute_type="int8", device="cpu")
client = OpenAI(api_key=OPENAI_KEY)

# Azure streaming TTS
async def tts_stream(text: str):
    logging.info("Starting TTS stream")
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        stream = speechsdk.audio.PullAudioOutputStream.create_pull_stream()
        audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config, audio_config)

        done = asyncio.Event()
        synthesizer.synthesis_completed.connect(lambda evt: done.set())
        synthesizer.speak_text_async(text)

        while not done.is_set():
            chunk = stream.read(4096)
            if chunk:
                yield chunk
            await asyncio.sleep(0.01)
        logging.info("TTS stream completed")
    except Exception as e:
        logging.error(f"TTS Streaming failed: {str(e)}")

# WebSocket handler
@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connected")
    buffer = b""

    try:
        while True:
            chunk = await websocket.receive_bytes()
            buffer += chunk

            if len(buffer) >= 32000:
                logging.info("Processing audio chunk for transcription")
                try:
                    audio_io = BytesIO(buffer)
                    segments, _ = whisper_model.transcribe(audio_io, beam_size=1, language="en")
                except Exception as e:
                    logging.error(f"Whisper transcription failed: {str(e)}")
                    continue

                for segment in segments:
                    text = segment.text.strip()
                    if not text:
                        continue

                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "data": text
                    }))
                    logging.info(f"Transcript: {text}")

                    try:
                        gpt_response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[{"role": "user", "content": text}],
                            stream=True
                        )

                        assistant_response = ""
                        for part in gpt_response:
                            delta = part.choices[0].delta.get("content", "")
                            if delta:
                                assistant_response += delta
                                await websocket.send_text(json.dumps({
                                    "type": "gpt",
                                    "data": delta
                                }))
                        logging.info(f"GPT-4 Response: {assistant_response[:150]}...")

                        # TTS streaming
                        async for audio_chunk in tts_stream(assistant_response):
                            await websocket.send_bytes(audio_chunk)

                    except Exception as e:
                        logging.error(f"GPT-4 error: {str(e)}")

                buffer = b""  # Clear buffer after processing

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
