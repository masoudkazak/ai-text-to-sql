"""OpenRouter-based text-to-SQL service."""

from openai import AsyncOpenAI

from core.config import settings


class LLMService:
    """Generate SQL from natural language."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

    async def text_to_sql(self, text: str, schema: str, allowed_tables: list[str]) -> str:
        """Call OpenRouter and return SQL only."""

        if not settings.OPENROUTER_API_KEY:
            return "UNSAFE_REQUEST"

        system_prompt = (
            "You are a SQL expert. Convert the user request to a single SQL query.\n"
            f"Database schema: {schema}\n"
            f"Tables this user can access: {allowed_tables}\n\n"
            "Rules:\n"
            "- Return ONLY the SQL query, nothing else\n"
            "- If the request is unsafe or impossible, return exactly: UNSAFE_REQUEST\n"
            "- Never use tables outside the allowed list\n"
            "- Prefer bind placeholders like :param_name in predicates\n"
        )

        resp = await self.client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        content = (resp.choices[0].message.content or "UNSAFE_REQUEST").strip()
        return content
