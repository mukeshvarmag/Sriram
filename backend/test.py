import asyncio
import websockets
import soundfile as sf
from pydub import AudioSegment
import numpy as np
import json
import os

input_m4a = "sample.m4a"
converted_wav = "sample_converted.wav"
ws_url = "ws://localhost:3001/ws/audio"

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
    if not convert_m4a_to_wav(input_m4a, converted_wav):
        return

    # Read WAV file
    audio, samplerate = sf.read(converted_wav, dtype='int16')
    if samplerate != 16000:
        print("❌ Audio must be 16kHz.")
        return

    audio_bytes = audio.tobytes()
    chunk_size = 3200

    print("🌐 Connecting to", ws_url)
    async with websockets.connect(ws_url) as websocket:
        # Send init message
        await websocket.send(json.dumps({"type": "init", "voice": "en-US-JennyNeural"}))
        ack = await websocket.recv()
        print("✅ Server ACK:", ack)

        print(f"📤 Sending {len(audio_bytes)} bytes of audio...")
        for i in range(0, len(audio_bytes), chunk_size):
            await websocket.send(audio_bytes[i:i + chunk_size])
            await asyncio.sleep(0.05)  # small delay to mimic streaming

        print("📨 Awaiting server responses...")
        try:
            while True:
                msg = await websocket.recv()
                print("🟢 Received:", msg)
        except websockets.exceptions.ConnectionClosed:
            print("🔚 Connection closed by server.")

if __name__ == "__main__":
    asyncio.run(send_audio())
