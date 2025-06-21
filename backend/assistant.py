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

load_dotenv()
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        #turn_detection=MultilingualModel(),
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

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )
    logger.info(f"Greeting reply generated for room: {ctx.room}")

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))