import httpx
import logging
import random
from typing import List, Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an Autonomous Customer Support AI Copilot for our platform.
Your goal is to assist customers accurately, politely, and concisely."""

GROUNDED_RULES = """
GROUNDING INSTRUCTIONS:
1. Base your answer strictly on the Grounding Knowledge Context provided below.
2. For EVERY claim, policy detail, or fact you state, you MUST explicitly cite the source document name (e.g., "[Source: billing_policy.txt]") from the grounding context. Do not cite if the context doesn't contain the document name.
3. If no Grounding Knowledge Context is provided, or if the context does not contain enough information to answer the question, state clearly and honestly: "Based on our knowledge base, I am not certain about this information." and offer human escalation. Do not make up calculations, URLs, or policy limits.
"""

INTENT_PROMPT_INSTRUCTIONS = {
    "billing": (
        "TONE & STRUCTURE INSTRUCTION: You are handling a billing/financial inquiry. Be extremely precise, "
        "always prioritize numbers/dates/costs, and cite the exact document names and policy clauses "
        "contained in the context. Do not make up or assume calculations or numbers."
    ),
    "technical": (
        "TONE & STRUCTURE INSTRUCTION: You are handling a technical issue. Provide clear, step-by-step "
        "troubleshooting guidance. Assume the customer has basic technical literacy, and include specific "
        "configuration paths, parameters, or error codes referenced in the grounding context."
    ),
    "complaint": (
        "TONE & STRUCTURE INSTRUCTION: You are handling a customer complaint. Start with a brief, highly "
        "empathetic opening line (e.g., apologizing for the frustration). Keep your response concise, "
        "focus on direct solutions, and clearly outline the path to a human agent/escalation if they choose."
    ),
    "urgent": (
        "TONE & STRUCTURE INSTRUCTION: You are handling an urgent inquiry. Be direct, highly concise, "
        "apologize for the disruption, and guide them directly to the human escalation path."
    ),
    "account": (
        "TONE & STRUCTURE INSTRUCTION: You are handling an account/profile settings issue. Provide clear, "
        "secure guidance on updating settings, changing credentials, or navigating the account dashboard."
    ),
    "general": (
        "TONE & STRUCTURE INSTRUCTION: Be professional, helpful, polite, and clear."
    )
}

def get_system_prompt(intent: str, has_context: bool) -> str:
    prompt = SYSTEM_PROMPT
    if has_context:
        prompt += "\n" + GROUNDED_RULES
    else:
        prompt += "\n\nGROUNDING INSTRUCTIONS:\nNo grounding knowledge base context is available for this query. State honestly that you do not have sufficient information in the knowledge base and suggest human handoff."
    
    intent_instruction = INTENT_PROMPT_INSTRUCTIONS.get(intent, INTENT_PROMPT_INSTRUCTIONS["general"])
    prompt += "\n\n" + intent_instruction
    
    prompt += "\n\nANTI-REPETITION INSTRUCTIONS:\nAvoid starting with standard canned phrases like 'I understand your concern' or 'Thank you for reaching out'. Vary your sentence structures and rotate your opening sentences to sound natural, human, and fresh."
    return prompt

ROTATED_GREETINGS = [
    "Hello! Welcome to Support Copilot. I'm your AI assistant, here to answer your questions or assist with troubleshooting. How can I help you today?",
    "Hi there! Welcome to Support Copilot. What can I do for you today?",
    "Greetings! I'm here to assist you with any questions or issues. How can I help you?",
    "Hello! I'm your support assistant. What are we working on today?",
    "Hi! Thanks for reaching out to Support Copilot. How can I be of assistance today?"
]

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
            return random.choice(ROTATED_GREETINGS)
        
        # 2. Help/Capabilities
        if any(h in user_msg_lower for h in ["help", "helps", "can you do", "what can you", "how to use", "support"]):
            return (
                "I can assist you with a variety of support topics, including:\n\n"
                "• **Billing & Payments:** Inquiries about subscription plans, invoices, charges, or refunds.\n"
                "• **Technical Support:** Troubleshooting app issues, crashes, errors, or configuration problems.\n"
                "• **Account Settings:** Managing password resets, profile updates, and dashboard access.\n"
                "• **Knowledge Base:** Fetching relevant answers from uploaded support guides and policy documents.\n\n"
                "If your inquiry is urgent or requires human intervention, I will automatically escalate this chat and create a ticket for our support team."
            )
        
        # Fallback canned responses based on intent keyword
        if intent == "billing" or any(k in user_msg_lower for k in ["billing", "invoice", "charge", "payment", "refund", "subscription", "price"]):
            billing_options = [
                "For billing inquiries, subscription changes, or refund requests, please check your Account Settings under the 'Billing & Subscriptions' section. You can view all past invoices and active plans there. If you need an adjustment or a manual refund review, please let me know and I will escalate this to our billing team.",
                "To manage your billing, billing details, and plans, please visit your Account Dashboard's Billing section. If you have an unexpected charge or need to request a refund, let me know and I can get a support representative to look into it.",
                "Invoices, refund status, and plans are managed in your account dashboard under 'Billing'. Let me know if you need help with a specific transaction, and we can raise a ticket for our billing specialists."
            ]
            return random.choice(billing_options)
        elif intent == "technical" or any(k in user_msg_lower for k in ["technical", "bug", "crash", "error", "failed", "not working", "slow", "down", "issue"]):
            tech_options = [
                "For technical issues or errors, please ensure your application is running the latest version and try clearing your browser cache. If you are experiencing a persistent bug, please describe the steps to reproduce it or any error codes displayed so we can troubleshoot it effectively.",
                "If you are facing a crash or loading error, please check your internet connection, update the app, and clear cache. If that doesn't help, share the specific error message or screenshot details, and we can investigate further.",
                "We recommend performing a hard reload and checking the app settings. If the technical issue continues, please provide the exact steps or API error codes, and we will get our engineering team to review it."
            ]
            return random.choice(tech_options)
        elif intent == "account" or any(k in user_msg_lower for k in ["account", "profile", "password", "username", "login", "reset password"]):
            account_options = [
                "You can manage your account settings, change your password, update contact preferences, or customize your dashboard directly within your User Profile tab. If you are having trouble logging in or resetting your credentials, please let me know.",
                "To update your profile settings, email notifications, or credentials, please navigate to your dashboard's Settings page. If you are locked out or need 2FA assistance, tell me and we can escalate this to account security.",
                "Security settings, passwords, and profile details can be edited in your account profile. If you have trouble resetting your password or accessing your account, let me know so we can assist you."
            ]
            return random.choice(account_options)
        elif intent == "complaint":
            complaint_options = [
                "We sincerely apologize for any frustration or inconvenience this situation has caused. I have logged your concerns and flagged this conversation for direct manager review. A support lead will reach out to you shortly to resolve this.",
                "I am very sorry to hear about your negative experience. I've recorded your complaint and sent it to our customer care manager immediately. A team member will prioritize getting in touch with you.",
                "Please accept our apologies for the trouble. I have created a high-priority ticket for our manager to look into this right away. We will reach out shortly to ensure this is sorted out."
            ]
            return random.choice(complaint_options)
        elif intent == "urgent" or any(k in user_msg_lower for k in ["urgent", "emergency", "immediate", "asap"]):
            urgent_options = [
                "Your request has been classified as urgent. I am prioritizing this conversation and notifying a support specialist right away. Please provide any additional context or account details so they can assist you immediately upon connection.",
                "I've flagged this conversation as urgent and notified the support queue. A support agent will review your issue immediately. Please stay tuned or leave any extra details here.",
                "We are prioritizing your request. I am looping in an agent right now to address this. Please provide any account emails or invoice numbers to speed up the process."
            ]
            return random.choice(urgent_options)
        else:
            fallback_options = [
                f"Thank you for reaching out. I've noted your message: '{user_msg}'. Could you please provide a few more details or clarify if this relates to billing, account settings, or technical support? I'll do my best to help, or I can connect you with a human agent if needed.",
                f"Got it. Regarding '{user_msg}', could you share more details so I can find the best answer in our docs? Let me know if you would prefer to escalate to a human agent.",
                f"Thanks for your message. I'm here to help with billing, technical issues, or account settings. Could you describe your problem in a bit more detail?"
            ]
            return random.choice(fallback_options)

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
        
        sys_prompt = get_system_prompt(intent or "general", bool(context))
        prompt_messages = [{"role": "system", "content": sys_prompt}]
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
        
        sys_prompt = get_system_prompt(intent or "general", bool(context))
        if context:
            sys_prompt += f"\n\nGrounding Knowledge Context:\n{context}"
            
        formatted_messages = []
        for m in messages:
            if m["role"] in ["user", "assistant"]:
                formatted_messages.append({"role": m["role"], "content": m["content"]})
                
        payload = {
            "model": "claude-3-5-sonnet-20240620",
            "max_tokens": 1024,
            "system": sys_prompt,
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
        
        sys_prompt = get_system_prompt(intent or "general", bool(context))
        prompt_messages = [{"role": "system", "content": sys_prompt}]
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

class GeminiProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        if not settings.GEMINI_API_KEY:
            return "[Error: GEMINI_API_KEY missing]. " + await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        
        sys_prompt = get_system_prompt(intent or "general", bool(context))
        if context:
            sys_prompt += f"\n\nGrounding Knowledge Context:\n{context}"
            
        gemini_contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": m["content"]}]
            })
            
        payload = {
            "contents": gemini_contents,
            "systemInstruction": {
                "parts": [{"text": sys_prompt}]
            },
            "generationConfig": {
                "maxOutputTokens": 1024,
                "temperature": 0.3
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return "No response text received from Gemini."
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)

def get_llm_provider() -> BaseLLMProvider:
    provider_type = settings.LLM_PROVIDER.lower().strip()
    if provider_type == "ollama":
        return OllamaProvider()
    elif provider_type == "anthropic":
        return AnthropicProvider()
    elif provider_type == "openai":
        return OpenAIProvider()
    elif provider_type == "gemini":
        return GeminiProvider()
    else:
        return TemplateProvider()
