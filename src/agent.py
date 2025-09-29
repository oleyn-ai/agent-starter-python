from dotenv import load_dotenv
import logging

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, llm, function_tool
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



class Assistant(Agent):
    def __init__(self) -> None:
        # Create the weather tool
        @function_tool()
        async def get_weather(city: str) -> str:
            """
            Get the current weather for a given city.
            
            Args:
                city (str): The name of the city to get weather for
                
            Returns:
                str: Weather information for the city
            """
            logger.info(f"Weather requested for city: {city}")
            # Dummy weather API - always returns 70 degrees
            return f"The current weather in {city} is 70 degrees Fahrenheit with sunny skies."

        
        super().__init__(
            instructions="You are a helpful voice AI assistant. You can provide weather information for any city when asked. When users ask about the weather, use the get_weather function to get current weather data.",
            tools=[get_weather]
        )


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(
    #         voice="coral"
    #     )
    # )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` instead for best results
            noise_cancellation=noise_cancellation.BVC(), 
        ),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))