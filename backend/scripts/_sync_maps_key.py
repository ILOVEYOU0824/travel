from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BE = ROOT / "backend" / ".env"
FE = ROOT / "frontend" / ".env"


def main() -> None:
    fe_key = None
    for line in FE.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("VITE_GOOGLE_MAPS_API_KEY="):
            fe_key = line.split("=", 1)[1].strip().strip("\"'")
            break
    if not fe_key:
        raise SystemExit("frontend VITE_GOOGLE_MAPS_API_KEY missing")

    lines = BE.read_text(encoding="utf-8-sig").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        if line.startswith("GOOGLE_MAPS_API_KEY="):
            out.append(f"GOOGLE_MAPS_API_KEY={fe_key}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"GOOGLE_MAPS_API_KEY={fe_key}")
    text = "\n".join(out)
    if BE.read_text(encoding="utf-8-sig").endswith("\n"):
        text += "\n"
    BE.write_text(text, encoding="utf-8")
    print("synced OK; backend key end=", fe_key[-4:])


if __name__ == "__main__":
    main()
