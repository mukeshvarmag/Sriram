import asyncio
import websockets
import json
import os
from gtts import gTTS
from pydub import AudioSegment

input_m4a = "sample.m4a"
converted_wav = "sample_converted.wav"
ws_url = "ws://localhost:3001/ws/audio"

def generate_sample_m4a():
    print("🗣️ Generating sample.m4a via gTTS...")
    text = (
        "Hello! This is a longer test audio clip intended to test the Whisper transcription service. "
        "The purpose of this test is to ensure that audio streaming and speech recognition work properly. "
        "We are sending this data to the WebSocket server, and we expect to receive a transcription in return. "
        "If everything works correctly, this message should be clearly recognized and processed. "
        "This file is longer to stress test the server buffer handling and whisper transcription pipeline."
    )
    tts = gTTS(text)
    tts.save("sample.mp3")

    audio = AudioSegment.from_file("sample.mp3", format="mp3")
    audio.export(input_m4a, format="ipod")
    print("✅ sample.m4a generated successfully.")

def convert_m4a_to_wav(input_path, output_path):
    print("🔄 Converting .m4a to 16kHz mono PCM WAV...")
    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        return False

    try:
        audio = AudioSegment.from_file(input_path, format="m4a")
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio.export(output_path, format="wav")
        print(f"✅ Conversion complete: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False

async def send_audio():
    generate_sample_m4a()

    if not convert_m4a_to_wav(input_m4a, converted_wav):
        return

    with open(converted_wav, "rb") as f:
        audio_bytes = f.read()

    chunk_size = 3200

    print("🌐 Connecting to", ws_url)
    try:
        async with websockets.connect(ws_url, max_size=None) as websocket:
            await websocket.send(json.dumps({"type": "init", "voice": "en-US-JennyNeural"}))
            ack = await websocket.recv()
            print("✅ Server ACK:", ack)

            print(f"📤 Sending {len(audio_bytes)} bytes of audio...")
            for i in range(0, len(audio_bytes), chunk_size):
                try:
                    await websocket.send(audio_bytes[i:i + chunk_size])
                except Exception as e:
                    print(f"❌ Failed to send chunk at byte {i}: {e}")
                    break
                await asyncio.sleep(0.1)

            await asyncio.sleep(1)
            print("📨 Awaiting server responses...")
            try:
                while True:
                    msg = await websocket.recv()
                    print("🟢 Received:", msg)
            except websockets.exceptions.ConnectionClosed:
                print("🔚 Connection closed by server.")

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(send_audio())
