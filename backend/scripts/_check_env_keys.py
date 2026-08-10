from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    ROOT / "backend" / ".env",
    ROOT / "frontend" / ".env",
    ROOT / ".env",
]
WANT = {
    "GOOGLE_MAPS_API_KEY",
    "VITE_GOOGLE_MAPS_API_KEY",
    "GOOGLE_PLACES_API_KEY",
    "USE_MOCK_PLACES",
}


def clean(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def main() -> None:
    values: dict[str, str] = {}
    for path in FILES:
        label = f"{path.parent.name}/{path.name}"
        print("---", label)
        if not path.exists():
            print(" missing")
            continue
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = clean(value)
            if key not in WANT:
                continue
            fp = sha256(value.encode()).hexdigest()[:8]
            values[f"{label}:{key}"] = value
            print(
                f" {key}: len={len(value)} start={value[:7]} "
                f"end={value[-4:]} space={' ' in value} hash={fp}"
            )

    be = values.get("backend/.env:GOOGLE_MAPS_API_KEY", "")
    fe = values.get("frontend/.env:VITE_GOOGLE_MAPS_API_KEY", "")
    root = values.get("travel/.env:GOOGLE_PLACES_API_KEY", "")
    print("--- compare")
    print(" backend==frontend:", bool(be) and be == fe)
    print(" backend==root_places:", bool(be) and bool(root) and be == root)
    print(" tip: Places calls use backend GOOGLE_MAPS_API_KEY only")


if __name__ == "__main__":
    main()
