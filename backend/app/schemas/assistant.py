from pydantic import BaseModel


class AssistantRequest(BaseModel):
    message: str


class AssistantResponse(BaseModel):
    intent: str
    reply: str
