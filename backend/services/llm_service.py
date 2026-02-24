import re
import logging

from openai import AsyncOpenAI
import sqlglot

from core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

    async def text_to_sql(self, text: str, schema: str, allowed_tables: list[str]) -> str:
        if not settings.OPENROUTER_API_KEY:
            return "UNSAFE_REQUEST"

        system_prompt = (
            "You are an expert PostgreSQL SQL generator.\n"
            "Convert the user's natural-language request (Persian or English) into exactly ONE PostgreSQL SQL statement.\n"
            f"Database schema: {schema}\n"
            f"Tables user can access: {allowed_tables}\n\n"
            "Hard rules:\n"
            "1) Return ONLY SQL, no explanation, no markdown, no comments.\n"
            "2) Use only the allowed tables.\n"
            "3) Resolve table names from user text to actual schema table names. If user writes natural names with spaces/dashes/case variants, map them to the closest valid allowed table name (typically snake_case).\n"
            "4) Prefer safe SQL with WHERE conditions for UPDATE/DELETE when possible.\n"
            "5) If the user intent is explicit destructive DDL (DROP/TRUNCATE/ALTER), still return the corresponding SQL statement (do not replace it with UNSAFE_REQUEST).\n"
            "6) Return UNSAFE_REQUEST only when the request is gibberish/ambiguous/impossible to map to schema, or is explicit SQL injection payload.\n"
            "7) Do NOT return UNSAFE_REQUEST just because the request is write/delete.\n"
            "8) Output must be a single valid PostgreSQL statement.\n"
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
        logger.info("LLM raw response: %s", content)
        sql = self._normalize_sql_output(content)
        logger.info("LLM normalized SQL: %s", sql)
        if sql == "UNSAFE_REQUEST":
            return sql

        if self._is_single_valid_sql(sql):
            return sql

        repaired = await self._repair_sql(sql=sql, schema=schema, allowed_tables=allowed_tables)
        logger.info("LLM repaired SQL: %s", repaired)
        if repaired and self._is_single_valid_sql(repaired):
            return repaired

        return "UNSAFE_REQUEST"

    @staticmethod
    def _normalize_sql_output(content: str) -> str:
        if content.strip().upper() == "UNSAFE_REQUEST":
            return "UNSAFE_REQUEST"

        fence_match = re.search(r"```(?:sql)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
        if fence_match:
            return fence_match.group(1).strip()

        keyword_match = re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|WITH|DROP|ALTER|TRUNCATE)\b", content, flags=re.IGNORECASE)
        if keyword_match:
            return content[keyword_match.start() :].strip()

        return content.strip()

    @staticmethod
    def _is_single_valid_sql(sql: str) -> bool:
        try:
            stmts = sqlglot.parse(sql, read="postgres")
            return len(stmts) == 1
        except Exception:
            return False

    async def _repair_sql(self, sql: str, schema: str, allowed_tables: list[str]) -> str | None:
        prompt = (
            "Repair this SQL for PostgreSQL so it becomes exactly one valid statement.\n"
            "Keep the original intent.\n"
            "User request may be Persian or English.\n"
            "Resolve natural table names to real allowed schema names (spaces/case variants -> actual table, often snake_case).\n"
            "If intent is explicit destructive DDL, return valid DDL SQL rather than UNSAFE_REQUEST.\n"
            "Return UNSAFE_REQUEST only if intent is impossible or ambiguous.\n"
            "Return ONLY SQL or UNSAFE_REQUEST.\n"
            f"Schema: {schema}\n"
            f"Allowed tables: {allowed_tables}\n"
            f"SQL:\n{sql}"
        )
        resp = await self.client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        content = (resp.choices[0].message.content or "").strip()
        normalized = self._normalize_sql_output(content)
        if normalized.upper() == "UNSAFE_REQUEST":
            return None
        return normalized
