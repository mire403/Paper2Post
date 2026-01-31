from __future__ import annotations

from Paper2Post.prompt import ChatMessage, LLMClient, system_guardrails, user_instruction


def generate_linkedin_post(llm: LLMClient, paper_context: str) -> str:
    platform_brief = (
        "Write a LinkedIn technical post summarizing this paper.\n"
        "Tone: professional, engineering-led, pragmatic; explain trade-offs and implications.\n"
        "Format requirements:\n"
        "- 400-900 words.\n"
        "- Start with a 1-2 sentence hook (non-clickbait).\n"
        "- Use short paragraphs and bullets.\n"
        "- Include: what problem it addresses, how it works (high-level), what evidence/results (or 'Not specified'), where it could be useful in real systems, risks/limitations, and a clear takeaway.\n"
        "- End with 2 discussion questions for practitioners.\n"
        "- Avoid emojis, avoid excessive hashtags (max 3, optional).\n"
        "- Do not invent details.\n"
    )
    messages = [
        ChatMessage(role="system", content=system_guardrails()),
        ChatMessage(role="user", content=user_instruction(platform_brief, paper_context)),
    ]
    return llm.chat(messages, temperature=0.5)

