from pydantic import BaseModel
from typing import Optional

class ChatModel(BaseModel):
    message: str
    session_id: Optional[str] = None