"""Protected read-only assistant endpoints."""
from fastapi import APIRouter, Depends, Response
from app.models import ChatbotMessageRequest, ChatbotResponse, ChatbotStatus
from app.routers.auth import get_current_user
from app.services import chatbot_service

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"], dependencies=[Depends(get_current_user)])


@router.post("/message", response_model=ChatbotResponse,
             responses={503: {"model": ChatbotResponse}})
def message(payload: ChatbotMessageRequest, response: Response):
    response.headers["Cache-Control"] = "no-store"
    result = chatbot_service.answer_message(payload)
    if result.status == "unavailable":
        response.status_code = 503
    return result


@router.get("/status", response_model=ChatbotStatus)
def status(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return chatbot_service.get_assistant_status()
