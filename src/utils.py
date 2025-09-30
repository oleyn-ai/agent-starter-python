# # Register shutdown callback to dump history and session outcome at end
# import json
# import logging
# import os
# from datetime import datetime

# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

# async def write_transcript(session):

#     # Prepare a log filename (use room name + timestamp or something meaningful)
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     room_name = ctx.room.name
#     filename = f"conversation_{room_name}_{timestamp}.json"
#     os.makedirs("logs", exist_ok=True)
#     filepath = os.path.join("logs", filename)
#     logger.info(f"Will save conversation history to {filepath}")

#     try:
#         hist = session.history.to_dict()
#         userdata = session.userdata

#         # Create a comprehensive session record
#         session_record = {
#             "conversation_history": hist,
#             "session_outcome": {
#                 "wants_to_buy": userdata.wants_to_buy,
#                 "user_name": userdata.user_name,
#                 "phone_number": userdata.phone_number,
#                 "conversation_completed": userdata.conversation_completed,
#                 "timestamp": timestamp,
#                 "room_name": room_name
#             }
#         }
#     except Exception as e:
#         logger.error("Failed to get session data", exc_info=e)
#         return

#     with open(filepath, "w", encoding="utf-8") as f:
#         json.dump(session_record, f, indent=2, ensure_ascii=False)

#     # Log the outcome   
#     outcome_msg = f"Session completed - Room: {room_name}, "
#     if userdata.wants_to_buy is True:
#         outcome_msg += f"SALE: Customer {userdata.user_name} ({userdata.phone_number}) agreed to buy"
#     elif userdata.wants_to_buy is False:
#         outcome_msg += "NO SALE: Customer declined to buy"
#     else:
#         outcome_msg += "INCOMPLETE: No purchase decision recorded"

#     logger.info(outcome_msg)
#     logger.info(f"Saved transcript and outcome to {filepath}")
