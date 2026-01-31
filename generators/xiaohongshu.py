from __future__ import annotations

from Paper2Post.prompt import ChatMessage, LLMClient, system_guardrails, user_instruction


def generate_xiaohongshu(llm: LLMClient, paper_context: str) -> str:
    platform_brief = (
        "生成一篇“小红书风格”的论文解读。\n"
        "语气：亲和、口语、强结构化、面向聪明但不一定做该方向的读者；少术语堆砌，但技术点必须准确。\n"
        "格式要求：\n"
        "- 用中文输出。\n"
        "- 以一个抓人的标题开头（不夸张，不标题党）。\n"
        "- 先给 5 行以内的 TL;DR。\n"
        "- 然后用分节小标题（例如：这篇在解决什么/方法怎么做/结果是什么/我怎么复现/哪些坑与局限）。\n"
        "- 给出“复现/落地清单”：3-6 条可执行步骤。\n"
        "- 最后给出“适合谁看/不适合谁看”。\n"
        "- 绝不编造数据或结论；缺失信息用“（文中未明确）”。\n"
        "- 不要使用表情符号，不要使用夸张网络梗。\n"
    )
    messages = [
        ChatMessage(role="system", content=system_guardrails()),
        ChatMessage(role="user", content=user_instruction(platform_brief, paper_context)),
    ]
    return llm.chat(messages, temperature=0.6)

