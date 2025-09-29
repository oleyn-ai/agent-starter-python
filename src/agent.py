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
from config import SALES_AGENT_PROMPT, PRODUCT_INFO
from livekit.agents.voice import RunContext
from dataclasses import dataclass

@dataclass
class userInfo:
    user_name: str | None = None
    phone_number: str | None = None
    wants_to_buy: bool | None = None
    conversation_completed: bool = False


load_dotenv(".env.local")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SalesAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                SALES_AGENT_PROMPT + "This is the product information: " + PRODUCT_INFO +
                "\n\nYour goal is to persuade the customer to buy this product. "
                "Answer any questions they have about the product. "
                "Once you've presented the product and answered their questions, "
                "ask if they would like to purchase it. "
                "If they say yes, collect their name and phone number, then say goodbye. "
                "If they say no, politely thank them for their time and say goodbye."
            ),
        )

    @function_tool()
    async def record_purchase_decision(self, context: RunContext[userInfo], wants_to_buy: bool):
        """Use this tool when the customer has made a clear decision about whether they want to buy the product or not."""
        context.userdata.wants_to_buy = wants_to_buy
        if wants_to_buy:
            return "Great! I'll need to collect some information from you to complete the purchase."
        else:
            context.userdata.conversation_completed = True
            return "Thank you for your time! Have a wonderful day!"

    @function_tool()
    async def record_name(self, context: RunContext[userInfo], name: str):
        """Use this tool to record the customer's name after they've agreed to buy."""
        if not context.userdata.wants_to_buy:
            return "Please let me know if you'd like to purchase the product first."
        context.userdata.user_name = name
        return f"Thank you, {name}! Now I'll need your phone number."

    @function_tool()
    async def record_phone_number(self, context: RunContext[userInfo], phone_number: str):
        """Use this tool to record the customer's phone number after they've agreed to buy and provided their name."""
        if not context.userdata.wants_to_buy or not context.userdata.user_name:
            return "Please provide your name first after agreeing to the purchase."
        context.userdata.phone_number = phone_number
        context.userdata.conversation_completed = True
        return f"Perfect! Thank you {context.userdata.user_name}, we have your information. Someone will contact you at {phone_number} to complete the purchase. Have a great day!"


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession[userInfo](
        userdata=userInfo(),
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

    # Register shutdown callback to dump history and session outcome at end
    async def write_transcript():
        try:
            hist = session.history.to_dict()
            userdata = session.userdata

            # Create a comprehensive session record
            session_record = {
                "conversation_history": hist,
                "session_outcome": {
                    "wants_to_buy": userdata.wants_to_buy,
                    "user_name": userdata.user_name,
                    "phone_number": userdata.phone_number,
                    "conversation_completed": userdata.conversation_completed,
                    "timestamp": timestamp,
                    "room_name": room_name
                }
            }
        except Exception as e:
            logger.error("Failed to get session data", exc_info=e)
            return

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_record, f, indent=2, ensure_ascii=False)

        # Log the outcome
        outcome_msg = f"Session completed - Room: {room_name}, "
        if userdata.wants_to_buy is True:
            outcome_msg += f"SALE: Customer {userdata.user_name} ({userdata.phone_number}) agreed to buy"
        elif userdata.wants_to_buy is False:
            outcome_msg += "NO SALE: Customer declined to buy"
        else:
            outcome_msg += "INCOMPLETE: No purchase decision recorded"

        logger.info(outcome_msg)
        logger.info(f"Saved transcript and outcome to {filepath}")

    ctx.add_shutdown_callback(write_transcript)



    await session.start(
        room=ctx.room,
        agent=SalesAgent(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await session.generate_reply(
        instructions="Greet the user warmly and introduce the product you're selling. Be enthusiastic and helpful."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
