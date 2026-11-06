from __future__ import annotations

def with_system(messages: list[dict], system_prompt: str) -> list[dict]:
    return [{"role": "system", "content": system_prompt}] + list(messages)


def messages_to_text(messages: list[dict], tokenizer, add_generation_prompt: bool = False) -> str:
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=add_generation_prompt,
    )
