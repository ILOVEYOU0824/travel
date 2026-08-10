from dataclasses import dataclass
from os import environ
from pathlib import Path


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    google_places_api_key: str
    ai_max_tokens: int
    lodging_limit: int
    places_limit: int

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            gemini_api_key=environ.get("GEMINI_API_KEY", ""),
            gemini_model=environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            google_places_api_key=environ.get("GOOGLE_PLACES_API_KEY", ""),
            ai_max_tokens=int(environ.get("AI_MAX_TOKENS", "700")),
            lodging_limit=int(environ.get("LODGING_LIMIT", "5")),
            places_limit=int(environ.get("PLACES_LIMIT", "8")),
        )
