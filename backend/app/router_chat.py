import time
import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Conversation, Message, Ticket, KBDocument
from app.schemas import (
    ConversationResponse,
    MessageCreateRequest,
    ChatMessageResult,
    MessageResponse,
    FeedbackRequest
)
from app.auth import get_current_user
from app.intent import classify_intent, should_escalate
from app.rag import rag_engine
from app.llm import get_llm_provider
from app.config import settings

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return conversations

@router.get("/conversations/{id}", response_model=ConversationResponse)
def get_conversation(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@router.delete("/conversations/{id}")
def delete_conversation(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully"}

@router.post("/message", response_model=ChatMessageResult)
async def send_message(
    req: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    
    # 1. Obtain or create conversation
    if req.conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == req.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        title_summary = req.content[:35] + "..." if len(req.content) > 35 else req.content
        conv = Conversation(
            user_id=current_user.id,
            title=title_summary,
            status="open"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Intent Detection
    intent, intent_confidence = classify_intent(req.content)

    # 3. RAG Retrieval
    kb_doc_count = db.query(KBDocument).count()
    rag_results, top_rag_score = rag_engine.search(db, req.content, top_k=3) if kb_doc_count > 0 else ([], 0.0)
    has_rag_context = len(rag_results) > 0 and top_rag_score >= 0.05

    # 4. Auto-escalation Evaluation
    is_escalated, escalation_reason = should_escalate(
        intent=intent,
        intent_confidence=intent_confidence,
        rag_score=top_rag_score,
        rag_threshold=settings.RAG_CONFIDENCE_THRESHOLD,
        has_kb_docs=(kb_doc_count > 0)
    )

    if is_escalated:
        conv.status = "escalated"

        # Check if an open/in_progress ticket already exists
        existing_ticket = db.query(Ticket).filter(
            Ticket.conversation_id == conv.id,
            Ticket.status.in_(["open", "in_progress"])
        ).first()

        if not existing_ticket:
            priority = "urgent" if intent == "urgent" else ("high" if intent == "complaint" else "medium")
            new_ticket = Ticket(
                conversation_id=conv.id,
                user_id=current_user.id,
                intent=intent,
                priority=priority,
                reason=escalation_reason,
                status="open"
            )
            db.add(new_ticket)

    # 5. Format grounding context for LLM
    context_str = None
    if has_rag_context:
        context_str = "\n\n".join([f"- {r['content']}" for r in rag_results])

    # 6. Retrieve message history for LLM prompt context
    past_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history_payload = [{"role": m.role, "content": m.content} for m in past_messages]
    history_payload.append({"role": "user", "content": req.content})

    # 7. Generate bot response via LLM provider
    provider = get_llm_provider()
    bot_reply_content = await provider.generate_response(
        messages=history_payload,
        context=context_str,
        intent=intent,
        is_escalated=is_escalated,
        escalation_reason=escalation_reason
    )

    elapsed_ms = int((time.time() - start_time) * 1000)

    # 8. Save User Message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.content,
        intent=intent,
        intent_confidence=intent_confidence
    )
    db.add(user_msg)

    # 9. Save Bot Message with signature reasoning metrics
    bot_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=bot_reply_content,
        intent=intent,
        intent_confidence=intent_confidence,
        rag_grounded=has_rag_context,
        retrieval_score=top_rag_score if kb_doc_count > 0 else None,
        escalated=is_escalated,
        escalation_reason=escalation_reason if is_escalated else None,
        response_time_ms=elapsed_ms
    )
    db.add(bot_msg)

    conv.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user_msg)
    db.refresh(bot_msg)

    return ChatMessageResult(
        conversation_id=conv.id,
        user_message=MessageResponse.model_validate(user_msg),
        bot_message=MessageResponse.model_validate(bot_msg)
    )

@router.post("/resolve/{id}")
def resolve_conversation(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.status = "resolved"
    conv.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": "Conversation marked as resolved"}

@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.feedback not in [1, -1]:
        raise HTTPException(status_code=400, detail="Feedback must be 1 or -1")

    msg = (
        db.query(Message)
        .join(Conversation)
        .filter(Message.id == req.message_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found or unauthorized")

    msg.feedback = req.feedback
    db.commit()
    return {"message": "Feedback submitted successfully", "message_id": msg.id, "feedback": msg.feedback}
