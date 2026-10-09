from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


class SensorData(BaseModel):
    temperature: float
    humidity: float
    pressure: float
    gas: float
    light: int
    soil: int
    ph: float


class DetectionData(BaseModel):
    detection_id: Optional[int] = None
    disease: str
    confidence: float
    date: Optional[str] = None
    hour: Optional[str] = None


class StartSessionRequest(BaseModel):
    plant_type: str = Field(..., description="Type of plant the user is asking about, e.g. 'tomato'")


class DecisionRequest(BaseModel):
    note: Optional[str] = None


class RecommendedAction(BaseModel):
    device: str
    action: str
    duration_minutes: Optional[float] = None
    reason: Optional[str] = None


class ManualCommandRequest(BaseModel):
    device: str
    action: str
    duration_minutes: Optional[float] = None
    reason: Optional[str] = "manual override"


class AckCommandRequest(BaseModel):
    success: bool = True
    note: Optional[str] = None

# Chat history is conversational data only; system/tool roles are never accepted.
ChatbotIntent = Literal[
    "greenhouse_status", "recommendation_explanation", "history_query",
    "system_diagnostics", "disease_knowledge", "growth_knowledge",
    "system_help", "what_if", "general",
]


class ChatbotHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatbotMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: List[ChatbotHistoryMessage] = Field(default_factory=list, max_length=100)

    @field_validator("message")
    @classmethod
    def non_blank_message(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("message cannot be blank")
        return value

    @field_validator("history")
    @classmethod
    def bound_history(cls, value):
        return value[-10:]


class ChatbotResponse(BaseModel):
    status: Literal["ok", "unavailable", "data_unavailable"] = "ok"
    answer: str
    intent: ChatbotIntent
    sources_used: List[str] = Field(default_factory=list)


class ChatbotStatus(BaseModel):
    ok: bool
    provider: str
    checked_at: str
