from __future__ import annotations

from Paper2Post.prompt import ChatMessage, LLMClient, system_guardrails, user_instruction


def generate_twitter_thread(llm: LLMClient, paper_context: str) -> str:
    platform_brief = (
        "Generate a Twitter/X thread about this paper.\n"
        "Tone: crisp, technical, slightly enthusiastic, but zero hype.\n"
        "Format requirements:\n"
        "- Output 10-14 tweets.\n"
        "- Each tweet must be <= 280 characters.\n"
        "- Number tweets as '1/12', '2/12', ...\n"
        "- Include: problem, key idea, method sketch, main results, why it matters, limitations, and a short 'Who should care' tweet.\n"
        "- If metrics/datasets are missing, say 'Not specified in the provided text'.\n"
        "- Avoid emojis and avoid hashtags.\n"
    )
    messages = [
        ChatMessage(role="system", content=system_guardrails()),
        ChatMessage(role="user", content=user_instruction(platform_brief, paper_context)),
    ]
    return llm.chat(messages, temperature=0.4)

