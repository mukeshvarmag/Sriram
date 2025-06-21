import asyncio
import json
import os
import logging
from io import BytesIO
from typing import List, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from faster_whisper import WhisperModel
import azure.cognitiveservices.speech as speechsdk
from openai import OpenAI
import hashlib

# --- Load environment variables ---
load_dotenv()
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# --- Configure logging ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
key_hash = hashlib.sha256(OPENAI_KEY.encode()).hexdigest()[:8] if OPENAI_KEY else "NO_KEY"
logging.info(f"OpenAI API Key Loaded (hash): {key_hash}")

# --- Initialize FastAPI & Services ---
app = FastAPI()
whisper_model = WhisperModel("base", compute_type="int8", device="cuda" if os.environ.get("FORCE_CPU") != "1" else "cpu")
client = OpenAI(api_key=OPENAI_KEY)

# --- Conversation memory for context ---
class ConversationManager:
    def __init__(self):
        self.messages: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return self.messages.copy()

    def clear(self):
        self.messages.clear()

# --- Azure TTS Streaming ---
async def tts_stream(text: str, voice: str = "en-US-JennyNeural"):
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        speech_config.speech_synthesis_voice_name = voice
        stream = speechsdk.audio.PullAudioOutputStream.create_pull_stream()
        audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config, audio_config)

        done = asyncio.Event()
        synthesizer.synthesis_completed.connect(lambda evt: done.set())

        result_future = synthesizer.speak_text_async(text)
        result_future.get()

        while not done.is_set():
            chunk = await asyncio.to_thread(stream.read, 4096)
            if chunk:
                yield chunk
            await asyncio.sleep(0.01)

        stream.close()
        logging.info("TTS stream completed.")
    except Exception as e:
        logging.error(f"TTS Streaming failed: {str(e)}")
        raise

# --- WebSocket Streaming Handler ---
@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connected")
    buffer = b""
    conversation = ConversationManager()
    voice = "en-US-JennyNeural"  # Default

    try:
        while True:
            try:
                data = await websocket.receive()
            except RuntimeError as e:
                logging.error(f"Fatal WebSocket error: {str(e)}")
                break

            # Init/Control messages
            if "text" in data:
                try:
                    parsed = json.loads(data["text"])
                    if parsed.get("type") == "init":
                        voice = parsed.get("voice", "en-US-JennyNeural")
                        await websocket.send_text(json.dumps({"type": "ack", "data": "ready"}))
                        logging.info(f"Initialized voice: {voice}")
                        continue
                    elif parsed.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                        continue
                except Exception as e:
                    logging.warning(f"Ignored non-init text: {e}")
                    continue

            # Audio bytes
            elif "bytes" in data:
                buffer += data["bytes"]

            # Process when audio buffer is large enough (~1s @ 16kHz)
            if len(buffer) >= 32000:
                audio_io = BytesIO(bytes(buffer))
                buffer = b""

                try:
                    segments, _ = whisper_model.transcribe(audio_io, beam_size=1, language="en")
                    for segment in segments:
                        text = segment.text.strip()
                        if not text:
                            continue

                        await websocket.send_text(json.dumps({"type": "transcript", "data": text}))
                        logging.info(f"Transcript: {text}")
                        conversation.add_message("user", text)

                        # GPT Streaming
                        assistant_response = ""
                        try:
                            stream = client.chat.completions.create(
                                model="gpt-4",
                                messages=conversation.get_messages(),
                                stream=True
                            )
                            for part in stream:
                                if part.choices:
                                    delta = part.choices[0].delta.get("content", "")
                                    if delta:
                                        assistant_response += delta
                                        await websocket.send_text(json.dumps({
                                            "type": "gpt",
                                            "data": delta
                                        }))
                            logging.info(f"GPT-4 Response: {assistant_response[:100]}...")
                            conversation.add_message("assistant", assistant_response)

                            # Stream TTS
                            async for audio_chunk in tts_stream(assistant_response, voice):
                                await websocket.send_bytes(audio_chunk)

                        except Exception as e:
                            logging.error(f"GPT-4 Error: {str(e)}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "data": f"GPT-4 error: {str(e)}"
                            }))
                except Exception as e:
                    logging.error(f"Whisper error: {str(e)}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": f"Transcription error: {str(e)}"
                    }))

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected.")
    except Exception as e:
        logging.error(f"Fatal WebSocket error: {str(e)}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": f"Unexpected server error: {str(e)}"
        }))
    finally:
        conversation.clear()
