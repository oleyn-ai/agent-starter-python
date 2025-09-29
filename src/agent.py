from dotenv import load_dotenv
import logging
import os
import json
from datetime import datetime

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(".env.local")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Assistant(Agent):
    def __init__(self) -> None:
        @function_tool()
        async def get_weather(city: str) -> str:
            logger.info(f"Weather requested for city: {city}")
            return f"The current weather in {city} is 70 degrees Fahrenheit with sunny skies."

        super().__init__(
            instructions=(
                "You are a helpful voice AI assistant. "
                "You can provide weather information for any city when asked. "
                "When users ask about the weather, use the get_weather function to get current weather data."
            ),
            tools=[get_weather],
        )


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        # optionally enable TTS‐aligned transcripts:
        # use_tts_aligned_transcript=True,
    )

    # Prepare a log filename (use room name + timestamp or something meaningful)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    room_name = ctx.room.name
    filename = f"conversation_{room_name}_{timestamp}.json"
    os.makedirs("logs", exist_ok=True)
    filepath = os.path.join("logs", filename)
    logger.info(f"Will save conversation history to {filepath}")

    # Register shutdown callback to dump history at end
    async def write_transcript():
        try:
            hist = session.history.to_dict()
        except Exception as e:
            logger.error("Failed to get session.history", exc_info=e)
            return

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved transcript to {filepath}")

    ctx.add_shutdown_callback(write_transcript)



    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
