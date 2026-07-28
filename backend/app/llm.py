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
        user_msg_lower = user_msg.lower().strip()

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
        
        # 1. Greetings
        if any(greet in user_msg_lower for greet in ["hello", "hi", "hey", "greetings", "good morning", "good afternoon"]):
            return (
                "Hello! Welcome to Support Copilot. I'm your AI assistant, here to answer your questions "
                "or assist with troubleshooting. How can I help you today?"
            )
        
        # 2. Help/Capabilities
        if any(h in user_msg_lower for h in ["help", "helps", "can you do", "what can you", "how to use", "support"]):
            return (
                "I can assist you with a variety of support topics, including:\n\n"
                "• 💳 **Billing & Payments:** Inquiries about subscription plans, invoices, charges, or refunds.\n"
                "• ⚙️ **Technical Support:** Troubleshooting app issues, crashes, errors, or configuration problems.\n"
                "• 👤 **Account Settings:** Managing password resets, profile updates, and dashboard access.\n"
                "• 📚 **Knowledge Base:** Fetching relevant answers from uploaded support guides and policy documents.\n\n"
                "If your inquiry is urgent or requires human intervention, I will automatically escalate this chat and create a ticket for our support team."
            )
        
        # Fallback canned responses based on intent keyword
        if intent == "billing" or any(k in user_msg_lower for k in ["billing", "invoice", "charge", "payment", "refund", "subscription", "price"]):
            return (
                "For billing inquiries, subscription changes, or refund requests, please check your Account Settings "
                "under the 'Billing & Subscriptions' section. You can view all past invoices and active plans there. "
                "If you need an adjustment or a manual refund review, please let me know and I will escalate this to our billing team."
            )
        elif intent == "technical" or any(k in user_msg_lower for k in ["technical", "bug", "crash", "error", "failed", "not working", "slow", "down", "issue"]):
            return (
                "For technical issues or errors, please ensure your application is running the latest version and try "
                "clearing your browser cache. If you are experiencing a persistent bug, please describe the steps to reproduce it "
                "or any error codes displayed so we can troubleshoot it effectively."
            )
        elif intent == "account" or any(k in user_msg_lower for k in ["account", "profile", "password", "username", "login", "reset password"]):
            return (
                "You can manage your account settings, change your password, update contact preferences, or customize your dashboard "
                "directly within your User Profile tab. If you are having trouble logging in or resetting your credentials, please let me know."
            )
        elif intent == "complaint":
            return (
                "We sincerely apologize for any frustration or inconvenience this situation has caused. I have logged your concerns "
                "and flagged this conversation for direct manager review. A support lead will reach out to you shortly to resolve this."
            )
        elif intent == "urgent" or any(k in user_msg_lower for k in ["urgent", "emergency", "immediate", "asap"]):
            return (
                "Your request has been classified as urgent. I am prioritizing this conversation and notifying a support specialist "
                "right away. Please provide any additional context or account details so they can assist you immediately upon connection."
            )
        else:
            return (
                f"Thank you for reaching out. I've noted your message: '{user_msg}'. "
                f"Could you please provide a few more details or clarify if this relates to billing, account settings, or technical support? "
                f"I'll do my best to help, or I can connect you with a human agent if needed."
            )

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
