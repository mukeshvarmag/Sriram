from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel
import openai
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
model = WhisperModel("base")

@app.websocket("/ws/audio")
async def stream_audio(websocket: WebSocket):
    await websocket.accept()
    audio_buffer = b""

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            audio_buffer += audio_chunk

            # Transcribe every ~50KB (~0.5s of audio)
            if len(audio_buffer) >= 50000:
                with open("temp.wav", "wb") as f:
                    f.write(audio_buffer)
                audio_buffer = b""

                segments, _ = model.transcribe("temp.wav")
                text = "".join([seg.text for seg in segments])
                await websocket.send_text(f"[STT] {text}")

                # Now stream GPT reply token by token
                await stream_gpt_response(websocket, text)

    except WebSocketDisconnect:
        print("Client disconnected")


async def stream_gpt_response(websocket: WebSocket, prompt: str):
    messages = [{"role": "user", "content": prompt}]
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=messages,
        stream=True
    )

    tts_buffer = ""
    async for chunk in response:
        if "content" in chunk.choices[0].delta:
            token = chunk.choices[0].delta.content
            await websocket.send_text(f"[GPT] {token}")
            tts_buffer += token

            if len(tts_buffer.split()) > 10:
                audio = await synthesize_tts(tts_buffer)
                await websocket.send_bytes(audio)
                tts_buffer = ""

async def synthesize_tts(text: str):
    tts = openai.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
    )
    return tts.content
