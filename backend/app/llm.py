import httpx
import logging
from typing import List, Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an Autonomous Customer Support AI Copilot for our platform.
Your goal is to assist customers accurately, politely, and concisely.

Rules:
1. Base your answer strictly on the Grounding Knowledge Context provided below if relevant.
2. If no Grounding Knowledge Context is provided or if the context does not contain enough information to answer the user's question, state honestly that you do not have sufficient information in the knowledge base and offer to connect them with a human agent.
3. Be professional, helpful, and clear.
"""

class BaseLLMProvider:
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        raise NotImplementedError

class TemplateProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        user_msg = messages[-1]["content"] if messages else ""

        if is_escalated:
            reason_text = f" (Reason: {escalation_reason})" if escalation_reason else ""
            return (
                f"I understand your issue regarding '{intent or 'your inquiry'}' is important. "
                f"I have automatically escalated this conversation to a human support agent for priority handling{reason_text}. "
                f"A team member will review your ticket shortly. Is there any additional detail you'd like to add?"
            )
        
        if context:
            # Simple template response summarizing context
            return (
                f"Based on our knowledge base:\n\n{context}\n\n"
                f"I hope this helps! Please let me know if you need further clarification."
            )
        
        # Fallback canned responses based on intent keyword
        if intent == "billing":
            return "For billing inquiries, invoices, or refund requests, please check your Account Settings under 'Billing'. If you require further assistance, our team is here to help."
        elif intent == "technical":
            return "For technical issues, please ensure your application is updated to the latest version and clear your browser cache. If the issue persists, let us know your system specs."
        elif intent == "account":
            return "You can update your profile, change passwords, and manage notification preferences directly from your Profile Dashboard."
        elif intent == "complaint":
            return "We sincerely apologize for any frustration caused. I have logged your issue and notified our support leads to look into this immediately."
        elif intent == "urgent":
            return "Your urgent request has been prioritized. A support specialist is being notified."
        else:
            return f"Thank you for contacting support! Regarding '{user_msg}', our automated assistant has processed your request. Please let us know if you need anything else."

class OllamaProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        
        prompt_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            prompt_messages.append({
                "role": "system",
                "content": f"Grounding Knowledge Context:\n{context}"
            })
            
        for m in messages:
            prompt_messages.append({"role": m["role"], "content": m["content"]})
            
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": prompt_messages,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "No response content from Ollama.")
        except Exception as e:
            logger.error(f"Ollama provider error: {e}")
            # Fallback to template provider on connection error
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)

class AnthropicProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        if not settings.ANTHROPIC_API_KEY:
            return "[Error: ANTHROPIC_API_KEY missing]. " + await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        system_text = SYSTEM_PROMPT
        if context:
            system_text += f"\n\nGrounding Knowledge Context:\n{context}"
            
        formatted_messages = []
        for m in messages:
            if m["role"] in ["user", "assistant"]:
                formatted_messages.append({"role": m["role"], "content": m["content"]})
                
        payload = {
            "model": "claude-3-5-sonnet-20240620",
            "max_tokens": 1024,
            "system": system_text,
            "messages": formatted_messages
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content_blocks = data.get("content", [])
                if content_blocks:
                    return content_blocks[0].get("text", "")
                return "No response text received from Anthropic."
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)

class OpenAIProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        if not settings.OPENAI_API_KEY:
            return "[Error: OPENAI_API_KEY missing]. " + await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            prompt_messages.append({
                "role": "system",
                "content": f"Grounding Knowledge Context:\n{context}"
            })
            
        for m in messages:
            if m["role"] in ["user", "assistant"]:
                prompt_messages.append({"role": m["role"], "content": m["content"]})
                
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": prompt_messages,
            "max_tokens": 1024
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return "No response text received from OpenAI."
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)

def get_llm_provider() -> BaseLLMProvider:
    provider_type = settings.LLM_PROVIDER.lower().strip()
    if provider_type == "ollama":
        return OllamaProvider()
    elif provider_type == "anthropic":
        return AnthropicProvider()
    elif provider_type == "openai":
        return OpenAIProvider()
    else:
        return TemplateProvider()
