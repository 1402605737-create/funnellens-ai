import json
import re
from typing import Any

import httpx

from app.database import settings


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = settings.deepseek_api_key
        self.model = settings.deepseek_model
        self.base_url = settings.deepseek_base_url.rstrip("/")

    async def complete_json(self, system_prompt: str, user_prompt: str) -> tuple[dict[str, Any] | None, str, bool]:
        if not self.api_key:
            return None, "DEEPSEEK_API_KEY is not configured.", True

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
            raw_content = body["choices"][0]["message"]["content"]
            parsed = extract_json(raw_content)
            return parsed, raw_content, False
        except Exception as exc:
            return None, str(exc), True


def extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("The model response did not contain a JSON object.")
    return json.loads(match.group(0))

