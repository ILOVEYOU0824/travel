import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.config import Settings


class AiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.gemini_api_key:
            return ""

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": self.settings.ai_max_tokens,
            },
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent"
            f"?key={self.settings.gemini_api_key}"
        )
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError):
            return ""

        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts).strip()
