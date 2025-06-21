from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
)

import os
import json
import logging

# ---- LOGGING SETUP: log to logs/agent.log ----
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, 'agent.log')
file_handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# ----------------------------------------------

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="""
        You are Sam, a senior product manager conducting a mock interview.
        Stay in character, ask thoughtful questions, and respond naturally.
        Do not reveal you are AI. Speak with curiosity and confidence.
        """)
        logger.info("Assistant initialized with interview instructions.")

async def entrypoint(ctx: agents.JobContext):
    logger.info(f"Entrypoint started for room: {ctx.room}")
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    logger.info(f"Session started for room: {ctx.room}")

    await ctx.connect()

    # Optional: Send greeting as soon as started
    ai_greeting = await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )
    logger.info(f"Greeting reply generated for room: {ctx.room} - Reply: {ai_greeting}")

    # ------ MAIN LOOP: logs transcript and reply ------
    async for turn in session:
        if not turn.transcript or not turn.transcript.strip():
            continue  # Skip empty turns

        logger.info(f"Transcript: {turn.transcript}")

        ai_reply = await session.generate_reply(prompt=turn.transcript)
        logger.info(f"Assistant reply: {ai_reply}")

        # If you want to send to frontend:
        # await session.room.local_participant.publish_data(
        #     json.dumps({"transcript": turn.transcript}).encode("utf-8"), kind="reliable"
        # )
        # await session.room.local_participant.publish_data(
        #     json.dumps({"reply": ai_reply}).encode("utf-8"), kind="reliable"
        # )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
