import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

# Auth Schemas
class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    credential: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Chat Schemas
class MessageCreateRequest(BaseModel):
    conversation_id: Optional[int] = None
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    rag_grounded: bool = False
    retrieval_score: Optional[float] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    response_time_ms: Optional[int] = None
    feedback: Optional[int] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

class ChatMessageResult(BaseModel):
    conversation_id: int
    user_message: MessageResponse
    bot_message: MessageResponse

class FeedbackRequest(BaseModel):
    message_id: int
    feedback: int  # 1 or -1

# KB Schemas
class KBDocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    chunk_count: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Ticket Schemas
class TicketResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    user_email: Optional[str] = None
    intent: str
    priority: str
    reason: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class TicketStatusUpdate(BaseModel):
    status: str  # "open" | "in_progress" | "closed"

# Metrics Schema
class MetricsSummaryResponse(BaseModel):
    total_conversations: int
    total_messages: int
    resolved_conversations: int
    escalated_conversations: int
    open_conversations: int
    resolution_rate: float
    escalation_rate: float
    avg_response_time_ms: float
    satisfaction_score: float
    open_tickets_count: int
