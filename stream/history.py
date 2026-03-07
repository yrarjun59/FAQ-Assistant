import json
from pathlib import Path

HISTORY_FILE = Path(__file__).parent / "chat_history.json"


def load() -> list:
    """Read messages from chat_history.json. Returns [] if missing or corrupt."""
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def save(messages: list) -> None:
    """Write full messages list to chat_history.json."""
    try:
        HISTORY_FILE.write_text(
            json.dumps(messages, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def clear() -> None:
    """Wipe chat_history.json back to an empty list."""
    try:
        HISTORY_FILE.write_text("[]", encoding="utf-8")
    except Exception:
        pass