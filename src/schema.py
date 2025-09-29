from dataclasses import dataclass

@dataclass
class userInfo:
    user_name: str | None = None
    phone_number: str | None = None
    wants_to_buy: bool | None = None
    conversation_completed: bool = False